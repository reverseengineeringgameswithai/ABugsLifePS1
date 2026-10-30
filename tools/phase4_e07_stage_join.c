#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <glob.h>
#include <inttypes.h>
#include <openssl/sha.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

typedef struct { uint8_t *p; size_t n; } Blob;
typedef struct {
    const uint8_t *c; size_t cn, pos;
    uint8_t *o; size_t on, ocap;
    uint32_t t2,t7,t0,t1;
    int error;
} Dec;

static uint32_t le32(const uint8_t *p) {
    return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static uint16_t le16(const uint8_t *p) { return (uint16_t)(p[0]|((uint16_t)p[1]<<8)); }
static uint32_t be32(const uint8_t *p) {
    return ((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3];
}
static Blob read_blob(const char *path) {
    FILE *f=fopen(path,"rb"); Blob b={0}; long n;
    if(!f){fprintf(stderr,"open %s: %s\n",path,strerror(errno));exit(2);}
    if(fseek(f,0,SEEK_END)||(n=ftell(f))<0||fseek(f,0,SEEK_SET))exit(2);
    b.n=(size_t)n;b.p=malloc(b.n?b.n:1);if(!b.p)exit(2);
    if(b.n && fread(b.p,1,b.n,f)!=b.n) exit(2);
    fclose(f); return b;
}
static uint8_t rd(Dec *d) {
    if(d->pos>=d->cn){d->error=1;return 0;} return d->c[d->pos++];
}
static void emit(Dec *d,uint8_t v) {
    if(d->on>=d->ocap){d->error=1;return;} d->o[d->on++]=v;
}
static void bit(Dec *d) {
    d->t2*=2; d->t7=(d->t2>>8)&1; d->t2&=0xff;
    if(d->t2==0){d->t2=rd(d);d->t2=d->t2*2+d->t7;d->t7=(d->t2>>8)&1;}
}
static int decompress(const uint8_t *c,size_t cn,uint8_t *out,size_t cap,size_t *got) {
    Dec d={c,cn,14,out,0,cap,0,0,0,0,0}; uint64_t steps=0;
    d.t7=1;d.t2=rd(&d);d.t2=d.t2*2+d.t7;d.t2*=2;d.t7=(d.t2>>8)&1;
    for(;;){
        if(++steps>20000000||d.error)return 0;
        d.t2*=2;d.t7=(d.t2>>8)&1;
        if(!d.t7){
            emit(&d,rd(&d));
            d.t2*=2;d.t7=(d.t2>>8)&1;
            if(!d.t7){emit(&d,rd(&d));continue;}
        }
        d.t2&=0xff;
        if(d.t2==0){
            d.t2=rd(&d);d.t2=d.t2*2+d.t7;d.t7=(d.t2>>8)&1;
            if(!d.t7){emit(&d,rd(&d));continue;}
        }
        d.t0=2;d.t1=0;
        bit(&d);
        if(!d.t7){
            bit(&d);d.t0=d.t0*2+d.t7;
            bit(&d);
            if(d.t7){
                d.t0--;
                bit(&d);d.t0=d.t0*2+d.t7;
                if(d.t0==9){
                    d.t0=3;d.t1=0;
                    do{bit(&d);d.t1=d.t1*2+d.t7;}while(d.t0--);
                    d.t1+=2;
                    while((int32_t)d.t1>=0){for(int q=0;q<4;q++)emit(&d,rd(&d));d.t1--;}
                    continue;
                }
            }
        } else {
            bit(&d);
            if(d.t7){
                d.t0++;
                bit(&d);
                if(d.t7){
                    d.t0=rd(&d);
                    if(d.t0==0){
                        bit(&d);
                        if(d.t7)continue;
                        *got=d.on;return !d.error;
                    }
                    d.t0+=8;
                }
            } else goto distance;
        }
        bit(&d);
        if(!d.t7)goto distance;
        bit(&d);d.t1=d.t1*2+d.t7;
        bit(&d);
        if(d.t7){
            bit(&d);d.t1=(d.t1*2+d.t7)|4;
            bit(&d);
            if(!d.t7){bit(&d);d.t1=d.t1*2+d.t7;}
        } else if(d.t1==0) {
            d.t1++;bit(&d);d.t1=d.t1*2+d.t7;
        }
        d.t1=((d.t1<<8)&0xff00)|(d.t1>>8);
distance:
        d.t1=rd(&d)|(d.t1&0xff00);
        {
            int64_t ref=(int64_t)d.on-(int64_t)d.t1-1;
            for(uint32_t i=0;i<d.t0;i++)emit(&d,ref+(int64_t)i<0?0:d.o[ref+i]);
        }
    }
}
static int actor_chunk(const Blob *raw,uint8_t **out,size_t *on,uint32_t *word0,
                       unsigned *found_index,unsigned *decode_failures) {
    size_t off=0;unsigned idx=0;*decode_failures=0;
    while(off+8<=raw->n){
        uint32_t a=be32(raw->p+off),b=be32(raw->p+off+4);
        if(a==0xffffffffu)return 0;
        if(off+14u+b>raw->n)return 0;
        uint8_t *p=calloc(a?a:1,1);size_t got=0;if(!p)exit(2);
        int ok=decompress(raw->p+off,14u+b,p,a,&got)&&got==a;
        if(!ok)(*decode_failures)++;
        if(ok && got>=32 && le32(p)==0x23u && (got-4)%28==0){
            *out=p;*on=got;*word0=a;*found_index=idx;return 1;
        }
        free(p);off+=14u+b;idx++;
    }
    return 0;
}
static size_t exeoff(uint32_t va,uint32_t load){return 0x800u+(size_t)(va-load);}
static uint32_t ex32(const Blob *e,uint32_t va,uint32_t load){
    size_t o=exeoff(va,load);return o+4<=e->n?le32(e->p+o):0;
}
static uint16_t ex16(const Blob *e,uint32_t va,uint32_t load){
    size_t o=exeoff(va,load);return o+2<=e->n?le16(e->p+o):0;
}
static void base_name(const char *raw,char *out,size_t n) {
    snprintf(out,n,"%s",raw);char *p=strstr(out,".RAW");if(p)snprintf(p,n-(size_t)(p-out),".BIN");
}
int main(void){
    Blob exe=read_blob("REBUILD/files/SCUS_942.88");uint32_t load=le32(exe.p+0x18);
    uint32_t ptr[40];for(unsigned i=0;i<40;i++)ptr[i]=ex32(&exe,0x80077af8u+i*4,load);
    uint16_t call_code=ex16(&exe,0x80077612u,load);
    struct Call {uint32_t pc;unsigned slot,nearest;} calls[64];size_t nc=0;
    for(uint32_t pc=0x8007745cu;pc+4<0x80077af8u;pc+=2){
        uint16_t h=ex16(&exe,pc,load),arg=ex16(&exe,pc+2,load);
        if(h==call_code && arg>=1 && arg<=9 && pc!=0x80077862u){
            unsigned ni=0;for(unsigned i=0;i<40;i++)if(ptr[i]<=pc&&ptr[i]>=ptr[ni])ni=i;
            calls[nc++]=(struct Call){pc,(unsigned)arg,ni};
        }
    }
    printf("{\n  \"schema\":\"abl.phase4.e07.stage_join.v2\",\n");
    printf("  \"call_encoding\":{\"encoded_opcode\":%u,\"known_anchor\":\"0x80077612\","
           "\"candidates\":%zu,\"uses\":[",call_code,nc);
    for(size_t i=0;i<nc;i++){if(i)putchar(',');printf("{\"pc\":\"0x%08" PRIx32
        "\",\"slot\":%u,\"nearest_program_entry\":%u}",calls[i].pc,calls[i].slot,calls[i].nearest);}
    printf("]},\n  \"stages\":[\n");
    glob_t g={0};glob("REBUILD/files/LEVEL*/LEVEL*.RAW",0,NULL,&g);
    unsigned campaign[256]={0};int first_stage=1;size_t stages=0,ok=0,bad=0;
    for(size_t fi=0;fi<g.gl_pathc;fi++){
        char bin[512];base_name(g.gl_pathv[fi],bin,sizeof(bin));if(access(bin,R_OK))continue;
        stages++;Blob raw=read_blob(g.gl_pathv[fi]);uint8_t *c=NULL;size_t cn=0;uint32_t want=0;
        unsigned chunk_index=0,decomp_failed=0;
        int good=actor_chunk(&raw,&c,&cn,&want,&chunk_index,&decomp_failed);if(!first_stage)printf(",\n");first_stage=0;
        printf("    {\"raw\":\"%s\",\"overlay\":\"%s\",\"actor_table_found\":%s",
               g.gl_pathv[fi],bin,good?"true":"false");
        if(!good){printf(",\"decode_failures\":%u}",decomp_failed);bad++;free(raw.p);continue;}ok++;
        int marker=cn>=4&&le32(c)==0x23u;size_t nr=(cn>=4)?(cn-4)/28:0;unsigned counts[256]={0},ids[256]={0};size_t active=0;
        for(size_t i=0;i<nr;i++){
            const uint8_t *r=c+4+i*28;int nz=0;for(unsigned j=0;j<28;j++)nz|=r[j];
            if(nz){active++;counts[r[13]]++;ids[r[12]]++;campaign[r[13]]++;}
        }
        printf(",\"chunk_index\":%u,\"decode_failures\":%u,\"decompressed_size\":%u,\"marker_ok\":%s,\"records\":%zu,\"active\":%zu,"
               "\"program_index_counts\":{",chunk_index,decomp_failed,want,marker?"true":"false",nr,active);
        int f=1;for(unsigned i=0;i<256;i++)if(counts[i]){if(!f)putchar(',');printf("\"%u\":%u",i,counts[i]);f=0;}
        printf("},\"actor_id_counts\":{");f=1;for(unsigned i=0;i<256;i++)if(ids[i]){if(!f)putchar(',');printf("\"%u\":%u",i,ids[i]);f=0;}
        printf("},\"nearest_entry_call_slots\":{");f=1;
        for(unsigned pi=0;pi<40;pi++)if(counts[pi]){
            unsigned mask=0;for(size_t ci=0;ci<nc;ci++)if(calls[ci].nearest==pi)mask|=1u<<(calls[ci].slot-1);
            if(mask){if(!f)putchar(',');printf("\"%u\":[",pi);int fs=1;for(unsigned s=1;s<=9;s++)if(mask&(1u<<(s-1))){if(!fs)putchar(',');printf("%u",s);fs=0;}putchar(']');f=0;}
        }
        printf("}}");free(c);free(raw.p);
    }
    printf("\n  ],\n  \"campaign\":{\"stage_pairs\":%zu,\"actor_table_found\":%zu,\"chunk31_failed\":%zu,"
           "\"program_index_counts\":{",stages,ok,bad);
    int f=1;for(unsigned i=0;i<256;i++)if(campaign[i]){if(!f)putchar(',');printf("\"%u\":%u",i,campaign[i]);f=0;}
    printf("},\"out_of_40_range\":[");f=1;for(unsigned i=40;i<256;i++)if(campaign[i]){if(!f)putchar(',');printf("%u",i);f=0;}
    printf("]}\n}\n");globfree(&g);free(exe.p);return 0;
}
