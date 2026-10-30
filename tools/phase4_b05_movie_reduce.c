#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>

enum { PLAYER_N=168, PLANT_N=960, REC_N=16+PLAYER_N+PLANT_N };
typedef struct { uint32_t sample, emu_frame; uint64_t cycle; uint8_t p[PLAYER_N], plants[PLANT_N]; } Rec;
static uint16_t u16(const uint8_t *p){ return (uint16_t)(p[0]|p[1]<<8); }
static int16_t s16(const uint8_t *p){ return (int16_t)u16(p); }
static uint32_t u32(const uint8_t *p){ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static int32_t s32(const uint8_t *p){ return (int32_t)u32(p); }
static int load(FILE *f, Rec *r){
  uint8_t h[16]; if(fread(h,1,16,f)!=16) return 0;
  r->sample=u32(h); r->emu_frame=u32(h+4); r->cycle=(uint64_t)u32(h+8)|((uint64_t)u32(h+12)<<32);
  return fread(r->p,1,PLAYER_N,f)==PLAYER_N && fread(r->plants,1,PLANT_N,f)==PLANT_N;
}
static const uint8_t *type10(const Rec *r){
  for(int i=0;i<20;i++){ const uint8_t *s=r->plants+i*0x30; if(u16(s)==10 && u16(s+2)!=0) return s; }
  return NULL;
}
int main(int argc,char **argv){
  if(argc!=2){fprintf(stderr,"usage: %s frames.bin\n",argv[0]); return 2;}
  FILE *f=fopen(argv[1],"rb"); if(!f){perror(argv[1]);return 1;} uint8_t magic[8];
  if(fread(magic,1,8,f)!=8 || memcmp(magic,"B05F\1\0\0\0",8)){fprintf(stderr,"bad input\n");return 1;}
  Rec a[527]; int n=0; while(n<527 && load(f,&a[n])) n++; fclose(f);
  printf("records=%d first_emu=%u last_emu=%u\n",n,a[0].emu_frame,a[n-1].emu_frame);
  int boost_first=-1,boost_last=-1,max_rise=INT_MIN,max_rise_f=-1,near_count=0;
  int min_dist2=INT_MAX,min_dist_f=-1; int stable_first=-1,stable_last=-1,stable_best=0;
  printf("type10 slot chronology (frame:type,state,extra,base_xyz):\n");
  int last_slot=-1,last_state=-1,last_extra=-1;
  for(int k=0;k<n;k++){
    const uint8_t *s=type10(&a[k]); if(!s) continue; int slot=(int)((s-a[k].plants)/0x30);
    int state=u16(s+2), extra=u16(s+0x2e); int bx=s32(s+8), by=s32(s+12), bz=s32(s+16);
    int x=s32(a[k].p), y=s32(a[k].p+4), z=s32(a[k].p+8), vy=s32(a[k].p+0x30);
    int dx=x-bx,dz=z-bz; long long d2=(long long)dx*dx+(long long)dz*dz;
    int rise=by-y;
    if(slot!=last_slot||state!=last_state||extra!=last_extra){printf("  %d:s%d st%d ex0x%x base=(%d,%d,%d)\n",k,slot,state,extra,bx,by,bz);last_slot=slot;last_state=state;last_extra=extra;}
    if(d2<min_dist2){min_dist2=(int)d2;min_dist_f=k;}
    if(d2<(7680LL*7680LL)){near_count++; if(rise>max_rise){max_rise=rise;max_rise_f=k;}}
    if(vy==-2048){if(boost_first<0)boost_first=k;boost_last=k;}
  }
  printf("boost_vy_-2048=%d..%d\n",boost_first,boost_last);
  printf("closest_xz_frame=%d dist2=%d; near_frames=%d; max_near_rise=%d@%d\n",min_dist_f,min_dist2,near_count,max_rise,max_rise_f);
  printf("player transitions (only meaningful state/vy boundaries):\n");
  int last_vy=INT_MIN,last_mode=INT_MIN,last_statep=INT_MIN,last_ground=INT_MIN;
  for(int k=0;k<n;k++){
    int vy=s32(a[k].p+0x30), mode=s16(a[k].p+0x88), statep=s16(a[k].p+0x80), ground=u16(a[k].p+0x90);
    if(k==0 || vy!=last_vy || mode!=last_mode || statep!=last_statep || ground!=last_ground){
      if(k==0 || mode!=last_mode || statep!=last_statep || ground!=last_ground || vy==-2048 || last_vy==-2048 || vy==0 || last_vy==0)
        printf("  f%d y=%d vy=%d floor=%d state=%d mode=%d ground=0x%x\n",k,s32(a[k].p+4),vy,s32(a[k].p+0x48),statep,mode,ground);
      last_vy=vy;last_mode=mode;last_statep=statep;last_ground=ground;
    }
  }
  printf("stable-Y runs >=6 frames near type10 (range<=96):\n");
  for(int i=0;i<n;i++){
    const uint8_t *s=type10(&a[i]); if(!s) continue; int by=s32(s+12), bx=s32(s+8),bz=s32(s+16);
    int ymin=s32(a[i].p+4),ymax=ymin,j=i;
    for(;j+1<n;j++){
      int yy=s32(a[j+1].p+4); if(yy<ymin)ymin=yy;if(yy>ymax)ymax=yy;
      int xx=s32(a[j+1].p),zz=s32(a[j+1].p+8); long long d2=(long long)(xx-bx)*(xx-bx)+(long long)(zz-bz)*(zz-bz);
      if(ymax-ymin>96 || d2>14000LL*14000LL) break;
    }
    int len=j-i+1;
    if(len>=6){printf("  %d..%d len%d y=%d..%d rise=%d..%d vy_end=%d\n",i,j,len,ymin,ymax,by-ymax,by-ymin,s32(a[j].p+0x30));if(len>stable_best){stable_best=len;stable_first=i;stable_last=j;}i=j;}
  }
  printf("best_stable=%d..%d len=%d\n",stable_first,stable_last,stable_best);
  printf("selected every-10-frame track: f x y z vy floor state mode rise dx dz\n");
  for(int k=0;k<n;k+=10){ const uint8_t*s=type10(&a[k]); if(!s)continue; int bx=s32(s+8),by=s32(s+12),bz=s32(s+16);
    printf("%d %d %d %d %d %d %d %d %d %d %d\n",k,s32(a[k].p),s32(a[k].p+4),s32(a[k].p+8),s32(a[k].p+0x30),s32(a[k].p+0x48),s16(a[k].p+0x80),s16(a[k].p+0x88),by-s32(a[k].p+4),s32(a[k].p)-bx,s32(a[k].p+8)-bz);}
  return 0;
}
