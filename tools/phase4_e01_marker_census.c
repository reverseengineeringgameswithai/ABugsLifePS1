#include <dirent.h>
#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

static uint32_t u32(const unsigned char *p) {
  return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}
static int family(uint32_t m) {
  return m == 0x00040000u || m == 0x80040000u ||
         ((m & 0xfff0ffffu) == 0xc0000000u &&
          (((m >> 16) & 15u) == 4u || ((m >> 16) & 15u) == 6u ||
           ((m >> 16) & 15u) == 7u || ((m >> 16) & 15u) == 8u ||
           ((m >> 16) & 15u) == 9u));
}
struct agg { uint32_t m; uint64_t runs,recs,bytes; uint32_t minspan,maxspan; uint64_t aligned4, same_head, head_nonzero; };
static struct agg A[16]; static int AN;
static struct agg *agg(uint32_t m) {
  for (int i=0;i<AN;i++) if (A[i].m==m) return &A[i];
  A[AN]=(struct agg){.m=m,.minspan=UINT32_MAX}; return &A[AN++];
}
static int cmp(const void *a,const void*b){uint32_t x=((const struct agg*)a)->m,y=((const struct agg*)b)->m;return x>y?1:x<y?-1:0;}
static void scan(const char *path) {
  FILE *f=fopen(path,"rb"); if(!f)return; fseek(f,0,SEEK_END); long nz=ftell(f); rewind(f);
  if(nz<0){fclose(f);return;} size_t n=(size_t)nz; unsigned char *d=malloc(n); if(!d){fclose(f);return;}
  if(fread(d,1,n,f)!=n){free(d);fclose(f);return;} fclose(f);
  int printed=0;
  for(size_t o=0;o+0x18*3<=n;o+=4) {
    uint32_t m=u32(d+o+0x10), p0=u32(d+o+0x14);
    if(!family(m)||p0>=n)continue;
    if(o>=0x18 && u32(d+o-0x18+0x10)==m) {
      uint32_t pp=u32(d+o-0x18+0x14); if(pp<n && pp<p0) continue;
    }
    size_t c=1; uint32_t prev=p0;
    while(o+(c+1)*0x18<=n) {
      uint32_t mm=u32(d+o+c*0x18+0x10), p=u32(d+o+c*0x18+0x14);
      if (mm != m || p >= n || p <= prev) break;
      prev = p;
      c++;
    }
    if(c<3)continue;
    struct agg *a=agg(m); a->runs++; a->recs+=c;
    uint32_t first=p0,last=u32(d+o+(c-1)*0x18+0x14);
    uint32_t end=(uint32_t)n, span=end-last;
    for(size_t z=0;z+4<=n;z+=4){uint32_t q=u32(d+z);if(q>last&&q<end)end=q;}
    if(end>last)span=end-last;
    a->bytes+=(uint64_t)(last-first)+span; if(span<a->minspan)a->minspan=span;if(span>a->maxspan)a->maxspan=span;
    uint32_t h0=u32(d+first);
    for(size_t j=0;j<c;j++){uint32_t p=u32(d+o+j*0x18+0x14);a->aligned4+=(p%4)==0;a->same_head+=u32(d+p)==h0;a->head_nonzero+=u32(d+p)!=0;}
    if(!printed || c>=20) {
      printf("RUN %s off=%#zx n=%zu marker=%08" PRIx32 " payload=%08" PRIx32 "..%08" PRIx32 " heads=%08" PRIx32 ",%08" PRIx32 ",%08" PRIx32 "\n",
       path,o,c,m,p0,last,u32(d+p0),u32(d+u32(d+o+0x18+0x14)),u32(d+u32(d+o+0x30+0x14)));
      printed=1;
    }
    o += c*0x18-4;
  }
  free(d);
}
int main(void){
  const char *root="REBUILD/files"; DIR *d=opendir(root); if(!d){perror(root);return 1;} struct dirent *e;
  while((e=readdir(d))) if(!strncmp(e->d_name,"LEVEL",5)) {
    char dir[512];snprintf(dir,sizeof dir,"%s/%s",root,e->d_name);DIR *q=opendir(dir);if(!q)continue;struct dirent*x;
    while((x=readdir(q))) {size_t l=strlen(x->d_name);if(l<4||strcmp(x->d_name+l-4,".DAT"))continue;char p[1024];snprintf(p,sizeof p,"%s/%s",dir,x->d_name);scan(p);} closedir(q);
  } closedir(d); qsort(A,AN,sizeof A[0],cmp);
  puts("--- aggregate ---");
  for(int i=0;i<AN;i++)printf("%08" PRIx32 " runs=%" PRIu64 " recs=%" PRIu64 " approx_bytes=%" PRIu64 " terminal_span=%" PRIu32 "..%" PRIu32 " aligned4=%" PRIu64 "/%" PRIu64 " same_first_head=%" PRIu64 "/%" PRIu64 " nonzero_head=%" PRIu64 "/%" PRIu64 "\n",
    A[i].m,A[i].runs,A[i].recs,A[i].bytes,A[i].minspan,A[i].maxspan,A[i].aligned4,A[i].recs,A[i].same_head,A[i].recs,A[i].head_nonzero,A[i].recs);
  return 0;
}
