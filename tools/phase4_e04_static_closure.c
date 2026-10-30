#include <dirent.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint32_t rd32(const uint8_t *p) {
  return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}
static int32_t s32(const uint8_t *p) { return (int32_t)rd32(p); }
typedef struct { uint8_t *d; size_t n; uint32_t base, code_off, code_n; } Image;
static void die(const char *s) { fprintf(stderr, "%s\n", s); exit(1); }
static Image load_exe(const char *p) {
  FILE *f=fopen(p,"rb"); if(!f)die("open exe"); fseek(f,0,SEEK_END); long z=ftell(f); rewind(f);
  Image x={0}; x.n=(size_t)z; x.d=malloc(x.n); if(!x.d||fread(x.d,1,x.n,f)!=x.n)die("read exe"); fclose(f);
  if(x.n<0x800||rd32(x.d)!=0x582d5350u)die("bad PS-X EXE");
  x.base=rd32(x.d+0x18);x.code_off=0x800;x.code_n=rd32(x.d+0x1c);
  if((uint64_t)x.code_off+x.code_n>x.n)die("bad EXE size");
  return x;
}
static uint32_t at(const Image*x,uint32_t pc) {
  if(pc<x->base||pc-x->base+4>x->code_n)die("PC out of range");
  return rd32(x->d+x->code_off+(pc-x->base));
}
static uint32_t jal_target(uint32_t pc,uint32_t w) { return ((pc+4)&0xf0000000u)|((w&0x03ffffffu)<<2); }
static int is_mem(uint32_t w) {
  unsigned o=w>>26; return o==0x20||o==0x21||o==0x23||o==0x24||o==0x25||o==0x28||o==0x29||o==0x2b;
}
static const char *mem_name(uint32_t w) {
  switch(w>>26){case 0x20:return"lb";case 0x21:return"lh";case 0x23:return"lw";case 0x24:return"lbu";case 0x25:return"lhu";case 0x28:return"sb";case 0x29:return"sh";case 0x2b:return"sw";default:return"?";}
}
static int is_store(uint32_t w){unsigned o=w>>26;return o==0x28||o==0x29||o==0x2b;}
static void camera_field_census(const Image*x){
  static const uint16_t fields[]={0x18,0x1a,0x1e,0x20,0x22,0x24,0x2a};
  puts("camera_fields:");
  for(size_t j=0;j<sizeof(fields)/sizeof(fields[0]);j++){
    printf("  +0x%02x",fields[j]);
    for(uint32_t pc=0x8004df18;pc<0x8004ea8c;pc+=4){uint32_t w=at(x,pc);unsigned rs=(w>>21)&31;
      if(is_mem(w)&&rs==18&&(uint16_t)w==fields[j])printf(" %c%s@%08"PRIx32,is_store(w)?'W':'R',mem_name(w),pc);
    }puts("");
  }
}
static void calls(const Image*x,uint32_t lo,uint32_t hi,uint32_t target,const char*name){
  unsigned n=0;printf("%s:",name);for(uint32_t pc=lo;pc<hi;pc+=4){uint32_t w=at(x,pc);if((w>>26)==3&&jal_target(pc,w)==target){printf(" %08"PRIx32,pc);n++;}}printf(" count=%u\n",n);
}
static void profile_table(const Image*x){
  puts("resident_profile_table_80077f40:");
  uint32_t off=x->code_off+(0x80077f40u-x->base);
  for(unsigned i=0;i<6;i++){const uint8_t*p=x->d+off+i*16;int32_t a=s32(p),b=s32(p+4),c=s32(p+8),d=s32(p+12);
    printf("  index=%u normal_distance=%"PRId32" alt_distance=%"PRId32" collision_bound=%"PRId32" vertical_offset=%"PRId32"\n",i,a,b,c,d);
  }
}
typedef struct { unsigned reads,writes; } RW;
static RW direct_addr_scan(const uint8_t*d,size_t n,uint16_t hi,uint16_t off){
  RW z={0};for(size_t i=0;i+4<=n;i+=4){uint32_t w=rd32(d+i);if(!is_mem(w)||(uint16_t)w!=off)continue;unsigned base=(w>>21)&31;int found=0;
    for(unsigned k=1;k<=12&&i>=4u*k;k++){uint32_t q=rd32(d+i-4u*k);if((q>>26)==0x0f&&((q>>16)&31)==base&&(uint16_t)q==hi){found=1;break;}}
    if(found){if(is_store(w))z.writes++;else z.reads++;}
  }return z;
}
static unsigned raw_jal_count(const uint8_t*d,size_t n,uint32_t target){
  unsigned c=0;uint32_t enc=0x0c000000u|((target>>2)&0x03ffffffu);for(size_t i=0;i+4<=n;i+=4)c+=rd32(d+i)==enc;return c;
}
int main(void){
  Image x=load_exe("REBUILD/files/SCUS_942.88");
  camera_field_census(&x);profile_table(&x);
  calls(&x,0x80010000,0x80082800,0x8004df18,"resident_calls_follow_8004df18");
  calls(&x,0x80010000,0x80082800,0x8004dd98,"resident_calls_setpiece_update_8004dd98");
  calls(&x,0x80010000,0x80082800,0x8004d9e8,"resident_calls_cinematic_start_8004d9e8");
  calls(&x,0x80010000,0x80082800,0x8004da94,"resident_calls_cinematic_start_polar_8004da94");
  RW sp=direct_addr_scan(x.d+x.code_off,x.code_n,0x8008,0x24dc), fl=direct_addr_scan(x.d+x.code_off,x.code_n,0x8009,0x0bee);
  printf("resident_direct_800824dc reads=%u writes=%u\n",sp.reads,sp.writes);
  printf("resident_direct_80090bee reads=%u writes=%u\n",fl.reads,fl.writes);
  DIR*root=opendir("REBUILD/files");if(!root)die("open files");struct dirent*e;unsigned bins=0,polar=0,sp_r=0,sp_w=0,fl_r=0,fl_w=0;
  while((e=readdir(root)))if(!strncmp(e->d_name,"LEVEL",5)){char dir[512];snprintf(dir,sizeof dir,"REBUILD/files/%s",e->d_name);DIR*q=opendir(dir);if(!q)continue;struct dirent*y;
    while((y=readdir(q))){size_t l=strlen(y->d_name);if(l<4||strcmp(y->d_name+l-4,".BIN"))continue;char p[1024];snprintf(p,sizeof p,"%s/%s",dir,y->d_name);FILE*f=fopen(p,"rb");if(!f)continue;fseek(f,0,SEEK_END);long z=ftell(f);rewind(f);uint8_t*d=malloc((size_t)z);if(!d)die("malloc");if(fread(d,1,(size_t)z,f)!=(size_t)z)die("read bin");fclose(f);bins++;unsigned c=raw_jal_count(d,(size_t)z,0x8004da94);if(c)printf("overlay_polar_calls %s count=%u\n",p,c);polar+=c;RW a=direct_addr_scan(d,(size_t)z,0x8008,0x24dc),b=direct_addr_scan(d,(size_t)z,0x8009,0x0bee);sp_r+=a.reads;sp_w+=a.writes;fl_r+=b.reads;fl_w+=b.writes;free(d);
    }closedir(q);
  }closedir(root);
  printf("overlays bins=%u polar_calls=%u direct_800824dc=%uR/%uW direct_80090bee=%uR/%uW\n",bins,polar,sp_r,sp_w,fl_r,fl_w);
  static const uint32_t keypcs[]={0x8004df40,0x8004df4c,0x8004df5c,0x8004dfdc,0x8004e064,0x8004e240,0x8004e8f8,0x8004e928,0x8004e92c,0x8004ea1c,0x8004ebf4,0x8004ebfc,0x8004ec10,0x8004ec54,0x8004ec5c};
  puts("key_words:");for(size_t i=0;i<sizeof(keypcs)/sizeof(keypcs[0]);i++)printf("  %08"PRIx32" %08"PRIx32"\n",keypcs[i],at(&x,keypcs[i]));
  free(x.d);return 0;
}
