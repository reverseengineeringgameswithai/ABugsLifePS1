#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>

typedef struct { uint8_t *p; size_t n, cap; } Buf;
static uint32_t be32(const uint8_t *p){return ((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3];}
static uint32_t le32(const uint8_t *p){uint32_t v; memcpy(&v,p,4); return v;}
static int32_t les32(const uint8_t *p){int32_t v; memcpy(&v,p,4); return v;}
static void put(Buf *b,uint8_t v){if(b->n==b->cap){b->cap=b->cap?b->cap*2:65536;b->p=realloc(b->p,b->cap);if(!b->p)exit(2);}b->p[b->n++]=v;}
static uint8_t hist(const Buf *b, int64_t i){return i>=0?(i<(int64_t)b->n?b->p[i]:0):0;}
static uint8_t *readall(const char *p,size_t *n){FILE*f=fopen(p,"rb");if(!f){perror(p);exit(2);}fseek(f,0,SEEK_END);long z=ftell(f);fseek(f,0,SEEK_SET);uint8_t*b=malloc((size_t)z);if(!b||fread(b,1,(size_t)z,f)!=(size_t)z)exit(2);fclose(f);*n=(size_t)z;return b;}

typedef struct {const uint8_t *c; size_t n,pos; Buf out; uint32_t t2,t7; int32_t t0,t1;} Dec;
static uint8_t rd(Dec*d){if(d->pos>=d->n){fprintf(stderr,"compressed input overrun\n");exit(2);}return d->c[d->pos++];}
static void bit(Dec*d){d->t2*=2;d->t7=(d->t2>>8)&1;d->t2&=0xff;if(!d->t2){d->t2=rd(d);d->t2=d->t2*2+d->t7;d->t7=(d->t2>>8)&1;}}
static Buf dechunk(const uint8_t*c,size_t n){
 Dec d={.c=c,.n=n,.pos=0x0e}; d.t7=1;d.t2=rd(&d);d.t2=d.t2*2+d.t7;d.t2*=2;d.t7=(d.t2>>8)&1;
 enum{MAIN,MATCH,MATCH_BODY,A470,LEN_C,E724,SWAP,DIST,LITRUN} s=MAIN; uint64_t guard=0;
 for(;;){if(++guard>20000000){fprintf(stderr,"decode guard\n");exit(2);}switch(s){
 case MAIN:d.t2*=2;d.t7=(d.t2>>8)&1;if(d.t7){s=MATCH;break;}put(&d.out,rd(&d));d.t2*=2;d.t7=(d.t2>>8)&1;if(!d.t7){put(&d.out,rd(&d));s=MAIN;}else s=MATCH;break;
 case MATCH:d.t2&=0xff;if(!d.t2){d.t2=rd(&d);d.t2=d.t2*2+d.t7;d.t7=(d.t2>>8)&1;if(!d.t7){put(&d.out,rd(&d));s=MAIN;break;}}s=MATCH_BODY;break;
 case MATCH_BODY:d.t0=2;d.t1=0;bit(&d);if(!d.t7){s=A470;break;}bit(&d);if(!d.t7){s=DIST;break;}d.t0++;bit(&d);if(d.t7){d.t0=rd(&d);if(!d.t0){bit(&d);if(d.t7){s=MAIN;break;}return d.out;}d.t0+=8;}s=LEN_C;break;
 case A470:bit(&d);d.t0=d.t0*2+(int)d.t7;bit(&d);if(!d.t7){s=LEN_C;break;}d.t0--;bit(&d);d.t0=d.t0*2+(int)d.t7;s=d.t0==9?LITRUN:LEN_C;break;
 case LEN_C:bit(&d);if(!d.t7){s=DIST;break;}bit(&d);d.t1=d.t1*2+(int)d.t7;bit(&d);if(d.t7){s=E724;break;}if(d.t1){s=SWAP;break;}d.t1++;bit(&d);d.t1=d.t1*2+(int)d.t7;s=SWAP;break;
 case E724:bit(&d);d.t1=d.t1*2+(int)d.t7;d.t1|=4;bit(&d);if(d.t7){s=SWAP;break;}bit(&d);d.t1=d.t1*2+(int)d.t7;s=SWAP;break;
 case SWAP:d.t1=((d.t1<<8)&0xff00)|((uint32_t)d.t1>>8);s=DIST;break;
 case DIST:{uint32_t dist=(uint32_t)(d.t1&0xff00)|rd(&d);int64_t ref=(int64_t)d.out.n-dist-1;for(int i=0;i<d.t0;i++)put(&d.out,hist(&d.out,ref+i));s=MAIN;break;}
 case LITRUN:d.t0=3;d.t1=0;do{bit(&d);d.t1=d.t1*2+(int)d.t7;d.t0--;}while(d.t0>=0);d.t1+=2;while(d.t1-->=0)for(int i=0;i<4;i++)put(&d.out,rd(&d));s=MAIN;break;
 }}
}
static uint32_t exe_word(const uint8_t*e,size_t n,uint32_t a){size_t o=0x800u+(size_t)(a-0x80010000u);if(o+4>n)exit(2);return le32(e+o);}
static uint32_t ovl_word(const uint8_t*e,size_t n,uint32_t base,uint32_t a){size_t o=(size_t)(a-base);if(o+4>n)exit(2);return le32(e+o);}
typedef struct {uint32_t a,w;const char*n;} Check;
int main(int argc,char**argv){
 if(argc!=4){fprintf(stderr,"usage: %s SCUS_942.88 LEVEL01/LEVEL.RAW BITS/MEMORY.BIN\n",argv[0]);return 2;}
 size_t en,rn,mn;uint8_t*exe=readall(argv[1],&en),*raw=readall(argv[2],&rn),*mem=readall(argv[3],&mn);
 Check c[]={
 {0x80038f38,0x90a30000,"gate_lbu"},{0x80038f5c,0x8c230560,"current_sector_lw"},{0x80038f78,0x84227e76,"region_code_lh"},
 {0x80049644,0x0c00e3ce,"query_call"},{0x8004965c,0x844223a0,"latch_guard"},{0x8004966c,0x10620015,"code2_branch"},
 {0x800496d8,0xa42223a0,"latch_store_1"},{0x80049704,0xa4222470,"timer_store_23"},{0x80049708,0x0c014265,"sfx_58_call"},
 {0x8004fef0,0x844223a0,"consumer_latch_read"},{0x8004ff04,0x84422470,"consumer_timer_read"},{0x8004ff48,0x0c011698,"transition_finalizer_call"}};
 int bad=0;for(size_t i=0;i<sizeof(c)/sizeof(c[0]);i++)if(exe_word(exe,en,c[i].a)!=c[i].w)bad++;
 size_t off=0;Buf ch={0};uint32_t declared=0;int chunks=0;while(off+8<=rn){uint32_t w0=be32(raw+off);if(w0==0xffffffffu)break;uint32_t w1=be32(raw+off+4);if(off+(size_t)0x0e + w1>rn){fprintf(stderr,"bad chunk table\n");return 2;}if(chunks==32){declared=w0;ch=dechunk(raw+off,(size_t)0x0e + w1);}off+=(size_t)0x0e + w1;chunks++;}
 if(!ch.p||ch.n!=declared){fprintf(stderr,"chunk32 decode mismatch got=%zu declared=%u\n",ch.n,declared);return 2;}
 const size_t so=0x36570, stride=0x4c, count=189;if(so+count*stride>ch.n)return 2;int code2n=0,code2=-1,nonzero=0;int32_t ox=0,oy=0,oz=0;for(size_t i=0;i<count;i++){const uint8_t*s=ch.p+so+i*stride;int32_t code=les32(s+0x2c);if(code)nonzero++;if(code==2){code2n++;code2=(int)i;ox=les32(s+8);oy=les32(s+0xc);oz=les32(s+0x10);}}
 uint32_t result_call=ovl_word(mem,mn,0x800b5788,0x800b8750);if(result_call!=0x0c011698)bad++;
 printf("{\n");
 printf(" \"row\":\"F01_anthill\",\n \"asm_checks\":{\"count\":%zu,\"mismatches\":%d},\n",sizeof(c)/sizeof(c[0]),bad);
 printf(" \"query\":{\"function\":\"0x80038f38\",\"gate\":\"player+0x82 == 1\",\"current_sector\":\"0x80090560 + player_index*20\",\"runtime_sector_table\":\"0x800a7e48 stride 0x30\",\"region_code_offset\":\"+0x2e\"},\n");
 printf(" \"dispatch\":{\"function\":\"0x80048138\",\"region_code\":2,\"latch_store\":\"0x800496d8: 0x800823a0=1\",\"timer_store\":\"0x80049704: 0x80082470=23\",\"sfx_call\":\"0x80049708: id 58\"},\n");
 printf(" \"level01_source\":{\"chunk\":32,\"decoded_bytes\":%zu,\"sector_array_offset\":\"0x36570\",\"sector_stride\":76,\"authored_sector_count\":189,\"nonzero_region_codes\":%d,\"code2_count\":%d,\"code2_sector\":%d,\"source_origin\":[%d,%d,%d],\"runtime_origin\":[%d,%d,%d]},\n",ch.n,nonzero,code2n,code2,ox,oy,oz,ox*32,oy*32,oz*32);
 printf(" \"consumer\":{\"latch_read\":\"0x8004fef0\",\"timer_read\":\"0x8004ff04\",\"finalizer_call\":\"0x8004ff48\"},\n");
 printf(" \"results\":{\"overlay\":\"BITS/MEMORY.BIN\",\"function\":\"0x800b7da0..0x800b8788\",\"finalizer_callsite\":\"0x800b8750\",\"call_word\":\"0x%08x\"}\n}\n",result_call);
 return bad||code2n!=1||code2!=177||ox!=-5094||oy!=-5309||oz!=-3901;
}
