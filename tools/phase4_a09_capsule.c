#define _POSIX_C_SOURCE 200809L
#include <glob.h>
#include <inttypes.h>
#include <limits.h>
#include <openssl/sha.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zstd.h>

typedef struct{const uint8_t*p,*end;}R;
static void need(R*r,size_t n){if((size_t)(r->end-r->p)<n){fputs("truncated capsule\n",stderr);exit(3);}}
static const uint8_t*take(R*r,size_t n){need(r,n);const uint8_t*p=r->p;r->p+=n;return p;}
static uint8_t ru8(R*r){return *take(r,1);}static uint16_t ru16(R*r){const uint8_t*p=take(r,2);return p[0]|(uint16_t)p[1]<<8;}static uint32_t ru32(R*r){const uint8_t*p=take(r,4);return p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}static uint64_t ru64(R*r){uint64_t a=ru32(r),b=ru32(r);return a|(b<<32);}
static uint8_t*slurp(const char*path,size_t*n){FILE*f=fopen(path,"rb");if(!f){perror(path);exit(2);}fseek(f,0,SEEK_END);long z=ftell(f);rewind(f);uint8_t*p=malloc((size_t)z+1);if(!p||fread(p,1,(size_t)z,f)!=(size_t)z){fprintf(stderr,"read %s\n",path);exit(2);}fclose(f);p[z]=0;*n=(size_t)z;return p;}
typedef struct{uint8_t*p;uint32_t n;}Dom;
static uint8_t rd8(const Dom*d,uint32_t a){uint32_t o=a&0x1fffff;return o<d->n?d->p[o]:0;}
static uint16_t rd16(const Dom*d,uint32_t a){uint32_t o=a&0x1fffff;return o+2<=d->n?d->p[o]|(uint16_t)d->p[o+1]<<8:0;}
static uint32_t rd32(const Dom*d,uint32_t a){uint32_t o=a&0x1fffff;return o+4<=d->n?d->p[o]|(uint32_t)d->p[o+1]<<8|(uint32_t)d->p[o+2]<<16|(uint32_t)d->p[o+3]<<24:0;}
static int32_t rs32(const Dom*d,uint32_t a){return(int32_t)rd32(d,a);}
static void movie_square(const char*path,uint8_t*s,size_t cap){size_t n;char*b=(char*)slurp(path,&n),*p=b;while((p=strstr(p,"\"frame\""))){char*c=strchr(p,':');if(!c)break;unsigned f=(unsigned)strtoul(c+1,NULL,10);char*next=strstr(c+1,"\"frame\"");char*q=strstr(c+1,"\"square\"");if(q&&(!next||q<next)){char*v=strchr(q,':');if(v&&f<cap&&strstr(v,"true")==v+strspn(v,": \t\r\n"))s[f]=1;}p=c+1;}free(b);}
typedef struct{uint32_t start,end,off,seed;uint8_t mode;uint64_t frames,exact_xz;int32_t dy_min,dy_max;}Epoch;
typedef struct{uint32_t pc;uint64_t n;}PcCount;
static void addpc(PcCount*a,int*nn,uint32_t pc,uint64_t n){for(int i=0;i<*nn;i++)if(a[i].pc==pc){a[i].n+=n;return;}if(*nn<512){a[*nn]=(PcCount){pc,n};(*nn)++;}}
static uint64_t getpc(const PcCount*a,int nn,uint32_t pc){for(int i=0;i<nn;i++)if(a[i].pc==pc)return a[i].n;return 0;}
static int cmp_pc(const void*A,const void*B){const PcCount*a=A,*b=B;return a->n<b->n?1:a->n>b->n?-1:0;}
int main(int ac,char**av){if(ac!=3){fprintf(stderr,"usage: %s capsule_dir movie.json\n",av[0]);return 2;}uint8_t sq[4096]={0};movie_square(av[2],sq,sizeof sq);char pat[PATH_MAX];snprintf(pat,sizeof pat,"%s/chunks/*.tcap.zst",av[1]);glob_t g={0};if(glob(pat,0,NULL,&g)){fputs("no chunks\n",stderr);return 2;}Dom d[4]={{0}};char**names=NULL;uint32_t nn=0,mode0=0;uint64_t frames=0,hashes=0,detach_blocks=0,carry_region=0;uint32_t first=0,last=0,prev_off=UINT32_MAX;uint8_t prev_mode=0xff,prev_sq=0;Epoch ep[32]={{0}};int ne=0,cur=-1;PcCount pcs[512];int np=0;int drop_active=0,drop_settled=0;uint32_t drop_start=0;int32_t drop_x=0,drop_y=0,drop_z=0;uint64_t drop_max_d2=0;printf("EVENTS\n");
for(size_t fi=0;fi<g.gl_pathc;fi++){size_t cn;uint8_t*c=slurp(g.gl_pathv[fi],&cn);unsigned long long zn=ZSTD_getFrameContentSize(c,cn);if(zn==ZSTD_CONTENTSIZE_ERROR||zn==ZSTD_CONTENTSIZE_UNKNOWN)return 3;uint8_t*raw=malloc((size_t)zn);size_t got=ZSTD_decompress(raw,(size_t)zn,c,cn);free(c);if(ZSTD_isError(got)||got!=zn)return 3;R r={raw,raw+got};if(memcmp(take(&r,8),"DSTCAP01",8)||ru32(&r)!=1)return 3;uint32_t bm=ru32(&r);(void)ru64(&r);uint32_t n=ru32(&r);if(!names){mode0=bm;nn=n;names=calloc(n,sizeof*names);for(uint32_t i=0;i<n;i++){uint16_t z=ru16(&r);names[i]=calloc(z+1,1);memcpy(names[i],take(&r,z),z);}}else{if(bm!=mode0||n!=nn)return 3;for(uint32_t i=0;i<n;i++){uint16_t z=ru16(&r);if(strlen(names[i])!=z||memcmp(names[i],take(&r,z),z))return 3;}}
while(r.p<r.end){if(ru8(&r)!=1)return 3;uint64_t ef=ru64(&r),cycle=ru64(&r);uint32_t mf=ru32(&r),pc=ru32(&r),initial=ru32(&r);(void)ef;(void)cycle;(void)pc;(void)initial;for(uint32_t i=0;i<nn;i++)ru32(&r);for(int q=0;q<3;q++){uint32_t id=ru32(&r),sz=ru32(&r),runs=ru32(&r);const uint8_t*want=take(&r,32);if(id<1||id>3)return 3;if(!d[id].p){d[id].p=calloc(1,sz);d[id].n=sz;}if(d[id].n!=sz)return 3;for(uint32_t j=0;j<runs;j++){uint32_t off=ru32(&r),len=ru32(&r);if((uint64_t)off+len>sz)return 3;memcpy(d[id].p+off,take(&r,len),len);}uint8_t h[32];SHA256(d[id].p,sz,h);if(memcmp(h,want,32))return 4;hashes++;}
uint64_t bc=ru64(&r);for(uint64_t j=0;j<bc;j++){uint32_t a=ru32(&r);uint64_t count=ru64(&r);if(a>=0x80046cacu&&a<0x80046d24u)detach_blocks+=count;if(a>=0x80046000u&&a<0x80048000u){carry_region+=count;addpc(pcs,&np,a,count);}}
uint32_t off=rd32(&d[1],0x800a655c),seed=off?0x8009fd80u+off:0x800a07d0u;uint8_t cm=rd8(&d[1],0x800a65a3);int32_t px=rs32(&d[1],0x800a6500),py=rs32(&d[1],0x800a6504),pz=rs32(&d[1],0x800a6508);uint32_t sid=rd32(&d[1],seed);int32_t sx=rs32(&d[1],seed+4),sy=rs32(&d[1],seed+8),sz=rs32(&d[1],seed+12);uint16_t fl=rd16(&d[1],seed+0x5c);int32_t mvx=rs32(&d[1],seed+0x1c),mvy=rs32(&d[1],seed+0x20),mvz=rs32(&d[1],seed+0x24);
if(frames==0)first=mf;
last=mf;
if(off!=prev_off||cm!=prev_mode){printf("state mf=%u off=0x%08x mode=0x%02x seed=0x%08x id=%u p=(%d,%d,%d) s=(%d,%d,%d) d=(%d,%d,%d) motion=(%d,%d,%d) flags=0x%04x\n",mf,off,cm,seed,sid,px,py,pz,sx,sy,sz,sx-px,sy-py,sz-pz,mvx,mvy,mvz,fl);prev_off=off;prev_mode=cm;}
if(sq[mf]&&!prev_sq)printf("square_edge mf=%u carry=0x%08x mode=0x%02x seed=0x%08x d=(%d,%d,%d) motion=(%d,%d,%d) flags=0x%04x\n",mf,off,cm,seed,sx-px,sy-py,sz-pz,mvx,mvy,mvz,fl);
prev_sq=sq[mf];
if(off&&cur<0){if(drop_active){printf("drop_end mf=%u span=%u final=(%d,%d,%d) delta=(%d,%d,%d) max_d2=%"PRIu64"\n",mf,mf-drop_start,sx,sy,sz,sx-drop_x,sy-drop_y,sz-drop_z,drop_max_d2);drop_active=0;}if(ne>=32)return 5;cur=ne++;ep[cur]=(Epoch){mf,mf,off,seed,cm,0,0,INT_MAX,INT_MIN};printf("attach mf=%u off=0x%x seed=0x%x mode=0x%x\n",mf,off,seed,cm);}
if(!off&&cur>=0){ep[cur].end=mf-1;printf("detach mf=%u prior_epoch=%d duration=%u\n",mf,cur,ep[cur].end-ep[cur].start+1);cur=-1;drop_active=1;drop_settled=0;drop_start=mf;drop_x=sx;drop_y=sy;drop_z=sz;drop_max_d2=0;}
if(cur>=0){Epoch*e=&ep[cur];e->end=mf;e->frames++;int32_t dy=sy-py;if(dy<e->dy_min)e->dy_min=dy;if(dy>e->dy_max)e->dy_max=dy;if(sx==px&&sz==pz)e->exact_xz++;}
if(drop_active&&!off){int64_t dx=(int64_t)sx-drop_x,dy=(int64_t)sy-drop_y,dz=(int64_t)sz-drop_z;uint64_t d2=(uint64_t)(dx*dx+dy*dy+dz*dz);if(d2>drop_max_d2)drop_max_d2=d2;if(!drop_settled&&mf>drop_start&&mvx==0&&mvy==0&&mvz==0){printf("drop_first_zero_motion mf=%u after=%u pos=(%d,%d,%d) delta=(%d,%d,%d) flags=0x%04x\n",mf,mf-drop_start,sx,sy,sz,sx-drop_x,sy-drop_y,sz-drop_z,fl);drop_settled=1;}}
frames++;}
free(raw);}if(cur>=0)cur=-1;if(drop_active)printf("drop_end mf=%u span=%u final_state_end max_d2=%"PRIu64"\n",last,last-drop_start+1,drop_max_d2);printf("EPOCHS\n");for(int i=0;i<ne;i++)printf("epoch=%d frames=%u..%u duration=%"PRIu64" off=0x%x seed=0x%x mode_start=0x%x exact_xz=%"PRIu64"/%"PRIu64" dy=%d..%d\n",i,ep[i].start,ep[i].end,ep[i].frames,ep[i].off,ep[i].seed,ep[i].mode,ep[i].exact_xz,ep[i].frames,ep[i].dy_min,ep[i].dy_max);printf("DECISIVE_BLOCKS\n");const uint32_t decisive[]={0x80047764,0x80047784,0x80047874,0x80047c1c,0x80047c34,0x80047c4c,0x80047cd0,0x80047cd4,0x80047d0c,0x80046cac};for(unsigned i=0;i<sizeof decisive/sizeof decisive[0];i++)printf("pc=0x%08x blocks=%"PRIu64"\n",decisive[i],getpc(pcs,np,decisive[i]));qsort(pcs,(size_t)np,sizeof pcs[0],cmp_pc);printf("CARRY_REGION_TOP\n");for(int i=0;i<np&&i<40;i++)printf("pc=0x%08x blocks=%"PRIu64"\n",pcs[i].pc,pcs[i].n);printf("SUMMARY chunks=%zu frames=%"PRIu64" movie=%u..%u hashes=%"PRIu64" all_hashes_ok=true detach_blocks=%"PRIu64" carry_region_blocks=%"PRIu64" square_edges=",g.gl_pathc,frames,first,last,hashes,detach_blocks,carry_region);int edges=0;for(unsigned i=0;i<sizeof sq;i++)if(sq[i]&&(i==0||!sq[i-1]))edges++;printf("%d epochs=%d\n",edges,ne);globfree(&g);return 0;}
