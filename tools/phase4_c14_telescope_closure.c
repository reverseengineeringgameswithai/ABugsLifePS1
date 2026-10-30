/* Phase 4 C14 bounded-exhaustion verifier. C-only, pristine retail inputs. */
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { EXE_SKIP=0x800, EXE_BASE=0x80010000 };
static uint8_t *x; static size_t xn;
static uint32_t u32p(const uint8_t*p){uint32_t v;memcpy(&v,p,4);return v;}
static uint16_t u16p(const uint8_t*p){uint16_t v;memcpy(&v,p,2);return v;}
static int16_t s16p(const uint8_t*p){int16_t v;memcpy(&v,p,2);return v;}
static int32_t s32p(const uint8_t*p){int32_t v;memcpy(&v,p,4);return v;}
static uint32_t ex(uint32_t va){size_t o=EXE_SKIP+(size_t)(va-EXE_BASE);if(o+4>xn){fprintf(stderr,"EXE OOB\n");exit(2);}return u32p(x+o);}
struct pin{uint32_t pc,w;const char*why;};
static const struct pin pins[]={
 {0x80053CC4,0x0C015D88,"kind30/31 contact effect"},{0x80053CCC,0x3C028000,"consumed sentinel 0x80000000"},{0x80053CD0,0xAE420000,"source entry Y := consumed sentinel"},
 {0x80054558,0x8C4224DC,"activation reads shared state"},{0x80054560,0x1440000F,"activation allowed only at idle zero"},{0x8005456C,0xAC3E23CC,"latch one-based kind30 ordinal"},{0x80054574,0xAC2224DC,"sole direct -1 trigger store"},
 {0x8004D6C0,0x8C306DC8,"ordinal indexes path-pointer table"},{0x8004D740,0xAC2224DC,"trigger acknowledge -2"},{0x8004D748,0x84422388,"wait for transition channel zero"},{0x8004D774,0xAC2224DC,"flight timer := 252"},
 {0x8004D7AC,0x2405010C,"phase = 268-state"},{0x8004D7B4,0x00051103,"segment = phase >> 4"},{0x8004D7E4,0x30A5000F,"fraction = phase & 15"},{0x8004D7DC,0x8C870004,"waypoint N x"},{0x8004D7E0,0x8C620004,"waypoint N+1 x"},{0x8004D7F0,0x8C860008,"waypoint N y"},{0x8004D808,0x8C84000C,"waypoint N z"},{0x8004D83C,0xAC270BD8,"interpolated x -> actor mirror"},{0x8004D844,0xAC260BDC,"interpolated y -> actor mirror"},{0x8004D864,0xAC240BE0,"interpolated z -> actor mirror"},
 {0x8004D784,0x14620003,"state 13 test"},{0x8004D790,0xA4220BEC,"state 13 sets actor phase 4"},{0x8004D92C,0x2C4200CD,"skip window unsigned(state-15)<205"},{0x8004D93C,0x84422412,"read current pad word"},{0x8004D944,0x3042F000,"face-button mask"},{0x8004D954,0xAC2224DC,"early-return request state 14"},{0x8004D978,0x2442FFFF,"active countdown decrement"},{0x8004D99C,0xAC2224DC,"return phase := -120"},{0x8004D9BC,0xAC2324DC,"return phase increment"},{0x8004D9D0,0xAC2024DC,"return completes at idle zero"},
 {0x8005363C,0x8C4224DC,"mask renderer reads shared state"},{0x80053658,0x10400035,"idle skips mask"},{0x80053694,0x0C009A9A,"mask quadrant 1"},{0x800536C4,0x0C009A9A,"mask quadrant 2"},{0x800536F4,0x0C009A9A,"mask quadrant 3"},{0x80053720,0x0C009A9A,"mask quadrant 4"},
 {0x80054AB0,0xA0242362,"transition target channel 1"},{0x80054AE0,0x84422388,"transition current channel 1"},{0x80054B1C,0xA4222388,"transition channel moves toward target"},
 {0x8004B480,0x8C4224DC,"actor interaction path reads special-view state"},{0x8004B488,0x1440003B,"nonzero view suppresses interaction tail"},{0x8004F05C,0x8C4224DC,"gameplay update gate reads special-view state"},
 {0x8005B324,0xAC2024DC,"respawn clears state"},{0x8005B9D0,0xAC2024DC,"scene init clears state"}
};
static long recsz(const uint8_t*d,long n,long o){if(o<0||o+4>n)return -1;uint16_t c=u16p(d+o);int16_t t=s16p(d+o+2);return t>=0?(t==0x3f?4+(long)c*0x10:4+(long)c*0xc):((((long)3*c+1)>>1)<<2)+0x10;}
static const uint32_t expect[11][6]={
 {0},{0x94c,0xa10,0xad4},{0},{0x1508,0x15cc},{0x1af0,0x1bb4,0x1c78},{0x4a8,0x56c,0x630,0x6f4},{0},{0x7ac,0x870,0x934,0x9f8,0xabc,0xb80},{0},{0x698,0x75c,0x820},{0x654,0x718,0x7dc,0x8a0}
};
static const int nexp[11]={0,3,0,2,3,4,0,6,0,3,4};
static int datcheck(int lv){char p[96];snprintf(p,sizeof p,"REBUILD/files/LEVEL%02d/LEVEL.DAT",lv);FILE*f=fopen(p,"rb");if(!f){perror(p);return 1;}fseek(f,0,SEEK_END);long n=ftell(f);rewind(f);uint8_t*d=malloc((size_t)n);if(!d||fread(d,1,(size_t)n,f)!=(size_t)n)return 1;fclose(f);uint32_t nr=u32p(d);long o=4,k30=0;for(uint32_t i=0;i<nr;i++){long z=recsz(d,n,o);if(z<0||o+z>n){free(d);return 1;}if(s16p(d+o+2)==0x3f){uint16_t c=u16p(d+o);for(uint16_t j=0;j<c;j++)if(d[o+4+(long)j*0x10+0xc]==0x30)k30++;}o+=z;}uint32_t got[16];int ng=0;for(o=0;o+0xc4<=n;o+=4){uint32_t h=u32p(d+o);if((h&0xffff)!=0x10||(h>>16)<11)continue;int plausible=1;for(int q=0;q<48;q++){int32_t v=s32p(d+o+4+4*q);if(v < -200000 || v > 200000){plausible=0;break;}}if(plausible&&ng<16)got[ng++]=(uint32_t)o;}int bad=(k30!=nexp[lv]||ng!=nexp[lv]);for(int i=0;i<ng&&i<nexp[lv];i++)if(got[i]!=expect[lv][i])bad=1;printf("LEVEL%02d kind30=%ld paths=%d",lv,k30,ng);for(int i=0;i<ng;i++)printf(" %05x",got[i]);printf(" %s\n",bad?"FAIL":"OK");free(d);return bad;}
int main(void){FILE*f=fopen("REBUILD/files/SCUS_942.88","rb");if(!f){perror("SCUS");return 2;}fseek(f,0,SEEK_END);xn=(size_t)ftell(f);rewind(f);x=malloc(xn);if(!x||fread(x,1,xn,f)!=xn)return 2;fclose(f);int bad=0;for(size_t i=0;i<sizeof pins/sizeof pins[0];i++){uint32_t g=ex(pins[i].pc);if(g!=pins[i].w){printf("FAIL %08x got %08x want %08x %s\n",pins[i].pc,g,pins[i].w,pins[i].why);bad++;}}printf("ASM pins %zu/%zu %s\n",sizeof pins/sizeof pins[0]-(size_t)bad,sizeof pins/sizeof pins[0],bad?"FAIL":"OK");int acc=0,stores=0;for(size_t o=EXE_SKIP;o+4<=xn;o+=4){uint32_t w=u32p(x+o),op=w>>26;if((w&0xffff)==0x24dc&&((op>=32&&op<=38)||(op>=40&&op<=46))){acc++;if(op>=40)stores++;}}printf("0x800824DC direct-immediate census accesses=%d stores=%d (expected 24/10)\n",acc,stores);if(acc!=24||stores!=10)bad++;for(int lv=0;lv<=10;lv++)bad+=datcheck(lv);free(x);puts("C14: 25 telescopes, 25 authored paths; waypoint flight, early return, mask renderer, transition gate, one-shot source and reset boundary pinned.");return bad?1:0;}
