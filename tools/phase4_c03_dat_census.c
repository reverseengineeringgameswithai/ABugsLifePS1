#define _XOPEN_SOURCE 700
#include <ftw.h>
#include <openssl/evp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

static unsigned files, tables, totals[4];
static uint16_t u16(const uint8_t *p){return (uint16_t)(p[0]|((uint16_t)p[1]<<8));}
static int32_t s32(const uint8_t*p){return(int32_t)((uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24));}
static int kind_ok(uint8_t k){return(k>=0x10&&k<=0x14)||(k>=0x20&&k<=0x24)||(k>=0x29&&k<=0x31);}
static int valid(const uint8_t*f,size_t n,size_t off,uint16_t*c,unsigned out[4]){
 if(off+8>n||u16(f+off+2)!=0x3f)return 0;
 *c=u16(f+off);
 if(!*c||*c>4096||off+4u+(size_t)*c*16u>n)return 0;
 memset(out,0,4*sizeof(*out)); const uint8_t*e=f+off+4;
 for(unsigned i=0;i<*c;i++,e+=16){int32_t x=s32(e),y=s32(e+4),z=s32(e+8); if(!kind_ok(e[12])||e[13]>1||x<-10000000||x>10000000||y<-10000000||y>10000000||z<-10000000||z>10000000)return 0; if(e[12]>=0x10&&e[12]<=0x13)out[e[12]-0x10]++;}
 return 1;
}
static int visit(const char*p,const struct stat*st,int type,struct FTW*ftw){(void)ftw;if(type!=FTW_F||strcmp(strrchr(p,'/')?strrchr(p,'/')+1:p,"LEVEL.DAT"))return 0;files++;
 FILE*fp=fopen(p,"rb");if(!fp)return 1;uint8_t*f=malloc((size_t)st->st_size);if(!f||fread(f,1,(size_t)st->st_size,fp)!=(size_t)st->st_size)return 1;fclose(fp);
 size_t found_off=0;uint16_t count=0;unsigned found[4]={0};int hits=0;
 for(size_t off=0;off+8<=(size_t)st->st_size;off+=2){uint16_t c;unsigned v[4];if(!valid(f,(size_t)st->st_size,off,&c,v))continue;hits++;found_off=off;count=c;memcpy(found,v,sizeof(v));}
 if(hits>1){fprintf(stderr,"%s multiple tables\n",p);return 1;}if(hits){tables++;for(int i=0;i<4;i++)totals[i]+=found[i];printf("%s off=0x%zx entries=%u F=%u L=%u I=%u K=%u complete_set=%s\n",p,found_off,count,found[0],found[1],found[2],found[3],(found[0]&&found[1]&&found[2]&&found[3])?"yes":"no");}else printf("%s type3f=absent F=0 L=0 I=0 K=0\n",p);free(f);return 0;}
int main(int argc,char**argv){const char*root=argc>1?argv[1]:"REBUILD/files";if(nftw(root,visit,16,FTW_PHYS))return 1;printf("TOTAL files=%u tables=%u F=%u L=%u I=%u K=%u letters=%u\n",files,tables,totals[0],totals[1],totals[2],totals[3],totals[0]+totals[1]+totals[2]+totals[3]);return files?0:1;}
