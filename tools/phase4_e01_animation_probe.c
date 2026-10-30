#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <glob.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint32_t be32(const uint8_t *p){return ((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3];}
static uint32_t le32(const uint8_t *p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static uint16_t le16(const uint8_t *p){return (uint16_t)(p[0]|((uint16_t)p[1]<<8));}
static uint8_t *read_file(const char *p,size_t *n){FILE*f=fopen(p,"rb");long z;uint8_t*b;if(!f)return NULL;if(fseek(f,0,SEEK_END)||((z=ftell(f))<0)||fseek(f,0,SEEK_SET)){fclose(f);return NULL;}b=malloc((size_t)z+1);if(!b){fclose(f);return NULL;}if(fread(b,1,(size_t)z,f)!=(size_t)z){free(b);fclose(f);return NULL;}fclose(f);*n=(size_t)z;return b;}

typedef struct{const uint8_t*c;size_t cn,pos;uint8_t*out;size_t cap,on;unsigned t2,t7;int err;} Dec;
static unsigned rd(Dec*d){if(d->pos>=d->cn){d->err=1;return 0;}return d->c[d->pos++];}
static void put(Dec*d,unsigned v){if(d->on>=d->cap){d->err=1;return;}d->out[d->on++]=(uint8_t)v;}
static void bit(Dec*d){d->t2*=2;d->t7=(d->t2>>8)&1;d->t2&=0xff;if(d->t2==0){d->t2=rd(d);d->t2=d->t2*2+d->t7;d->t7=(d->t2>>8)&1;}}
static int decomp(const uint8_t*c,size_t cn,uint8_t*out,size_t cap){Dec d={c,cn,14,out,cap,0,0,0,0};int t0,t1,ref,i;unsigned low,hi;size_t steps=0;d.t7=1;d.t2=rd(&d);d.t2=d.t2*2+d.t7;d.t2*=2;d.t7=(d.t2>>8)&1;
MAIN: if(++steps>20000000||d.err)goto BAD;d.t2*=2;d.t7=(d.t2>>8)&1;if(d.t7)goto MATCH;put(&d,rd(&d));d.t2*=2;d.t7=(d.t2>>8)&1;if(!d.t7){put(&d,rd(&d));goto MAIN;}goto MATCH;
MATCH:d.t2&=0xff;if(d.t2==0){d.t2=rd(&d);d.t2=d.t2*2+d.t7;d.t7=(d.t2>>8)&1;if(d.t7)goto MATCH_BODY;put(&d,rd(&d));goto MAIN;}
MATCH_BODY:t0=2;t1=0;bit(&d);if(!d.t7)goto A470;bit(&d);if(!d.t7)goto DIST;t0++;bit(&d);if(d.t7){t0=(int)rd(&d);if(t0==0){bit(&d);if(d.t7)goto MAIN;goto DONE;}t0+=8;}goto LEN_C;
A470:bit(&d);t0=t0*2+(int)d.t7;bit(&d);if(!d.t7)goto LEN_C;t0--;bit(&d);t0=t0*2+(int)d.t7;if(t0==9)goto LITRUN;goto LEN_C;
LEN_C:bit(&d);if(!d.t7)goto DIST;bit(&d);t1=t1*2+(int)d.t7;bit(&d);if(d.t7)goto E724;if(t1!=0)goto SWAP;t1++;bit(&d);t1=t1*2+(int)d.t7;goto SWAP;
E724:bit(&d);t1=t1*2+(int)d.t7;t1|=4;bit(&d);if(d.t7)goto SWAP;bit(&d);t1=t1*2+(int)d.t7;
SWAP:t1=((t1<<8)&0xff00)|((t1>>8)&0xff);
DIST:hi=(unsigned)t1&0xff00;low=rd(&d);t1=(int)(hi|low);ref=(int)d.on-t1-1;for(i=0;i<t0;i++)put(&d,ref+i>=0?d.out[ref+i]:0);goto MAIN;
LITRUN:t0=3;t1=0;do{bit(&d);t1=t1*2+(int)d.t7;t0--;}while(t0>=0);t1+=2;while(t1>=0){for(i=0;i<4;i++)put(&d,rd(&d));t1--;}goto MAIN;
DONE:if(d.err||d.on!=cap)return -1;return 0;BAD:return -1;}

typedef struct{uint32_t pc,word;} Pin;
static int pin_asm(const char*path,const Pin*p,size_t np){FILE*f=fopen(path,"r");char line[512];size_t i;int ok=0;if(!f)return -1;while(fgets(line,sizeof line,f))for(i=0;i<np;i++){char a[32],w[32];snprintf(a,sizeof a,"0x%08x",p[i].pc);snprintf(w,sizeof w,"%08x",p[i].word);if(strstr(line,a)&&strstr(line,w))ok++;}fclose(f);return ok;}

int main(void){
 static const Pin loader[]={
 {0x8003b830,0x1b008216},{0x8003b838,0x08006226},{0x8003b83c,0x04006486},{0x8003b850,0x80200400},{0x8003b878,0x389622ac},{0x8003b898,0x385120ac}};
 static const Pin upload[]={
 {0x80026dfc,0x00240400},{0x80026e04,0x38964224},{0x80026e14,0x0000e28c},{0x80026e34,0x0000a68c},{0x80026e40,0x08004390},{0x80026e58,0x1000a3a7},{0x80026e88,0x00004284},{0x80026eac,0x02004294},{0x80026ec8,0x18004300},{0x80026ed8,0x18006500},{0x80026ef0,0xfb9b0008}};
 static const Pin driver[]={
 {0x80052578,0x10000424},{0x80052598,0x7d9b000c},{0x800525a0,0x11000424},{0x800525b8,0x12000424},{0x800525d0,0x13000424},{0x800525e4,0x14000424},{0x800525f4,0x02000424},{0x80052618,0x05000424},{0x80052614,0x06000424},{0x8005262c,0x20000424},{0x80052644,0x29000424},{0x8005265c,0x01004224},{0x80052660,0x0f004230},{0x80052664,0x01006324},{0x80052674,0x07006330}};
 int pa=pin_asm("asm/nonmatchings/resident/8003a318_FUNC_8003A318.s",loader,sizeof loader/sizeof*loader);
 int pb=pin_asm("asm/nonmatchings/resident/80026df4.s",upload,sizeof upload/sizeof*upload);
 int pc=pin_asm("asm/nonmatchings/resident/80052574.s",driver,sizeof driver/sizeof*driver);
 glob_t g={0};size_t fi;int first=1,total=0,bad=0;glob("REBUILD/files/LEVEL*/LEVEL*.RAW",0,NULL,&g);
 printf("{\n \"asm_pins\":{\"loader\":\"%d/%zu\",\"uploader\":\"%d/%zu\",\"driver\":\"%d/%zu\"},\n \"files\":[\n",pa,sizeof loader/sizeof*loader,pb,sizeof upload/sizeof*upload,pc,sizeof driver/sizeof*driver);
 for(fi=0;fi<g.gl_pathc;fi++){size_t n=0,off=0;uint8_t*raw=read_file(g.gl_pathv[fi],&n);int ci=0,file_count=0;if(!raw)continue;while(off+8<=n){uint32_t wn=be32(raw+off),cn;if(wn==0xffffffff)break;cn=be32(raw+off+4);if(!wn||!cn||off+14u+cn>n){bad++;break;}uint8_t*out=malloc(wn);if(!out||decomp(raw+off,14u+cn,out,wn)){free(out);bad++;break;}if(wn>=12&&le32(out)==0x22){int tile=(int16_t)le16(out+4);unsigned w=le16(out+8),h=le16(out+10);size_t fb=(size_t)w*h/2,frames=fb?(wn-12)/fb:0;if(!file_count){if(!first)printf(",\n");first=0;printf("  {\"file\":\"%s\",\"strips\":[",g.gl_pathv[fi]);}else printf(",");printf("{\"chunk\":%d,\"tile\":%d,\"w\":%u,\"h\":%u,\"frames\":%zu,\"size\":%u}",ci,tile,w,h,frames,wn);file_count++;total++;}free(out);off+=14u+cn;ci++;}if(file_count)printf("]}");free(raw);}globfree(&g);printf("\n ],\n \"summary\":{\"files_with_strips\":%d,\"strip_count\":%d,\"decode_errors\":%d}\n}\n",first?0:1,total,bad);return (pa!=(int)(sizeof loader/sizeof*loader)||pb!=(int)(sizeof upload/sizeof*upload)||pc!=(int)(sizeof driver/sizeof*driver)||bad)?1:0;}
