#include <dirent.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint16_t u16(const unsigned char *p) { return (uint16_t)(p[0] | p[1] << 8); }
static uint32_t u32(const unsigned char *p) {
  return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}
static int family(uint32_t m) {
  uint16_t hi = (uint16_t)(m >> 16);
  return (m & 0xffffu) == 0 && ((hi & 0x3fffu) >= 4u && (hi & 0x3fffu) <= 9u) &&
         ((hi & 0x3fffu) != 5u) && ((hi & 0xc000u) == 0 || (hi & 0xc000u) == 0x8000u ||
          (hi & 0xc000u) == 0xc000u);
}
struct agg {
  uint32_t marker;
  uint64_t payloads, decoded, batches, first_inherit, all_inherit;
  uint64_t first_explicit, first_explicit_match, explicit_batches, explicit_match;
  uint64_t effective_batches, effective_match_initial;
  uint32_t first_ctrl[8]; unsigned first_ctrl_n;
};
static struct agg A[32]; static int AN;
static struct agg *get(uint32_t m) {
  for (int i=0;i<AN;i++) if (A[i].marker==m) return &A[i];
  A[AN]=(struct agg){.marker=m}; return &A[AN++];
}
static int cmp(const void*a,const void*b){uint32_t x=((const struct agg*)a)->marker,y=((const struct agg*)b)->marker;return x>y?1:x<y?-1:0;}
static void payload(struct agg *a,const unsigned char*d,size_t n,uint32_t p,uint32_t lim) {
  a->payloads++;
  if (p+4>n || lim>n || lim<=p+4) return;
  uint32_t vc=u32(d+p); if(!vc || vc>100000u || (uint64_t)p+4u+(uint64_t)vc*12u>lim)return;
  uint32_t maxoff=vc*12u; size_t o=(size_t)p+4u+(size_t)maxoff; unsigned nb=0; int first=1, all_inherit=1;
  uint16_t initial=(uint16_t)(a->marker>>16)&31u, current=initial;
  while(o+4<=lim) {
    if(u32(d+o)==0xffffffffu) break;
    uint16_t ctrl=u16(d+o), cnt=u16(d+o+2); size_t base=o+4;
    int valid=cnt>=1 && (uint64_t)base+(uint64_t)cnt*16u<=lim;
    unsigned chk=cnt<2?cnt:2;
    for(unsigned q=0;valid&&q<chk;q++)for(unsigned k=0;k<4;k++){uint16_t v=u16(d+base+q*16u+k*2u);if(v>=maxoff||v%12u)valid=0;}
    if(!valid){o+=2;continue;}
    if(first && a->first_ctrl_n<8)a->first_ctrl[a->first_ctrl_n++]=ctrl;
    int inherit=(ctrl&0x8000u)!=0;
    if(first){if(inherit)a->first_inherit++;else{a->first_explicit++;if((ctrl&31u)==initial)a->first_explicit_match++;}}
    if(!inherit){all_inherit=0;current=ctrl&31u;a->explicit_batches++;if(current==initial)a->explicit_match++;}
    a->effective_batches++; if(current==initial)a->effective_match_initial++;
    a->batches++;nb++;first=0;o=base+(size_t)cnt*16u;
  }
  if(nb){a->decoded++;if(all_inherit)a->all_inherit++;}
}
static void scan(const char*path) {
  FILE*f=fopen(path,"rb");if(!f)return;fseek(f,0,SEEK_END);long z=ftell(f);rewind(f);if(z<=0){fclose(f);return;}
  size_t n=(size_t)z;unsigned char*d=malloc(n);if(!d){fclose(f);return;}if(fread(d,1,n,f)!=n){free(d);fclose(f);return;}fclose(f);
  for(size_t o=0;o+0x48<=n;o+=4){
    uint32_t m=u32(d+o+0x10),p0=u32(d+o+0x14);if(!family(m)||p0>=n)continue;
    if(o>=0x18&&u32(d+o-8)==m){uint32_t pp=u32(d+o-4);if(pp<n&&pp<p0)continue;}
    size_t c=1;uint32_t prev=p0;
    while(o+(c+1)*0x18<=n){uint32_t mm=u32(d+o+c*0x18+0x10),p=u32(d+o+c*0x18+0x14);if(mm!=m||p>=n||p<=prev)break;prev=p;c++;}
    if(c<3)continue;
    struct agg*a=get(m);
    for(size_t j=0;j<c;j++){uint32_t p=u32(d+o+j*0x18+0x14);uint32_t lim=(j+1<c)?u32(d+o+(j+1)*0x18+0x14):(uint32_t)n;payload(a,d,n,p,lim);}
    o+=c*0x18-4;
  }
  free(d);
}
int main(void){
  DIR*d=opendir("REBUILD/files");if(!d)return 1;struct dirent*e;
  while((e=readdir(d))) {
    if(strncmp(e->d_name,"LEVEL",5)) continue;
    char dir[512];snprintf(dir,sizeof dir,"REBUILD/files/%s",e->d_name);
    DIR*q=opendir(dir);if(!q)continue;struct dirent*x;
    while((x=readdir(q))) {
      size_t l=strlen(x->d_name);if(l<4||strcmp(x->d_name+l-4,".DAT"))continue;
      char p[1024];snprintf(p,sizeof p,"%s/%s",dir,x->d_name);scan(p);
    }
    closedir(q);
  }
  closedir(d);
  qsort(A,AN,sizeof A[0],cmp);
  for(int i=0;i<AN;i++){struct agg*a=&A[i];printf("%08" PRIx32 " initial_page=%u payloads=%" PRIu64 " decoded=%" PRIu64 " batches=%" PRIu64 " first_inherit=%" PRIu64 " all_inherit=%" PRIu64 " first_explicit_match=%" PRIu64 "/%" PRIu64 " explicit_match=%" PRIu64 "/%" PRIu64 " effective_initial=%" PRIu64 "/%" PRIu64 " samples=",
  a->marker,(unsigned)((a->marker>>16)&31u),a->payloads,a->decoded,a->batches,a->first_inherit,a->all_inherit,a->first_explicit_match,a->first_explicit,a->explicit_match,a->explicit_batches,a->effective_match_initial,a->effective_batches);
  for(unsigned j=0;j<a->first_ctrl_n;j++)printf("%s%04x",j?",":"",a->first_ctrl[j]);
  puts("");}
  return 0;
}
