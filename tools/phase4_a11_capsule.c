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

typedef struct { const uint8_t *p, *end; } Reader;
typedef struct { uint8_t *p; uint32_t n; } Domain;
typedef struct { uint32_t ptr; int16_t knockback, hp; uint16_t flags; uint32_t id; } Actor;

static void fail(const char *s) { fprintf(stderr, "%s\n", s); exit(3); }
static const uint8_t *take(Reader *r, size_t n) {
    const uint8_t *p = r->p;
    if ((size_t)(r->end - r->p) < n) fail("truncated capsule");
    r->p += n;
    return p;
}
static uint8_t ru8(Reader *r) { return *take(r, 1); }
static uint16_t ru16(Reader *r) { const uint8_t *p=take(r,2); return p[0]|(uint16_t)p[1]<<8; }
static uint32_t ru32(Reader *r) { const uint8_t *p=take(r,4); return p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static uint64_t ru64(Reader *r) { uint64_t a=ru32(r), b=ru32(r); return a|(b<<32); }
static uint8_t *slurp(const char *path, size_t *n) {
    FILE *f=fopen(path,"rb"); long z; uint8_t *p;
    if (!f) { perror(path); exit(2); }
    if (fseek(f,0,SEEK_END) || (z=ftell(f))<0 || fseek(f,0,SEEK_SET)) fail("seek failed");
    p=malloc((size_t)z+1);
    if (!p || fread(p,1,(size_t)z,f)!=(size_t)z) fail("read failed");
    fclose(f); p[z]=0; *n=(size_t)z; return p;
}
static uint8_t rd8(const Domain *d, uint32_t a) { uint32_t o=a&0x1fffff; return o<d->n?d->p[o]:0; }
static uint16_t rd16(const Domain *d, uint32_t a) { uint32_t o=a&0x1fffff; return o+2<=d->n?d->p[o]|(uint16_t)d->p[o+1]<<8:0; }
static int16_t rs16(const Domain *d, uint32_t a) { return (int16_t)rd16(d,a); }
static uint32_t rd32(const Domain *d, uint32_t a) { uint32_t o=a&0x1fffff; return o+4<=d->n?d->p[o]|(uint32_t)d->p[o+1]<<8|(uint32_t)d->p[o+2]<<16|(uint32_t)d->p[o+3]<<24:0; }
static int32_t rs32(const Domain *d, uint32_t a) { return (int32_t)rd32(d,a); }
static int valid_actor(uint32_t p) { return p>=0x8009fd80u && p<0x8009fd80u+41u*0x84u && ((p-0x8009fd80u)%0x84u)==0; }
static int member(const Domain *ram, uint32_t p) {
    for (unsigned i=0;i<40;i++) if (rd32(ram,0x80090748u+4u*i)==p) return 1;
    return 0;
}
static Actor actor(const Domain *ram, unsigned i) {
    uint32_t p=0x8009fd80u+i*0x84u;
    Actor a={p,rs16(ram,p+0x6c),rs16(ram,p+0x6e),rd16(ram,p+0x5c),rd32(ram,p)};
    return a;
}
static uint64_t wanted(uint32_t pc, uint64_t n, uint64_t *hit) {
    static const uint32_t pcs[]={0x8004b2acu,0x8004b2c0u,0x80050994u,0x80057f44u,0x80058de4u,0x80058df4u,0x80058e08u,0x80058e10u,0x800498acu,0x80049b68u};
    for (unsigned i=0;i<sizeof(pcs)/sizeof(pcs[0]);i++) if(pc==pcs[i]) { hit[i]+=n; return n; }
    return 0;
}

int main(int ac, char **av) {
    char pat[PATH_MAX]; glob_t g={0}; Domain d[4]={{0}}; char **names=NULL;
    uint32_t nn=0, mode0=0, seed=0; uint64_t frames=0, hashes=0, totals[10]={0};
    Actor prev[41]={{0}}; int have_prev=0; uint32_t prev_table[40]={0};
    if(ac!=2){fprintf(stderr,"usage: %s capsule_dir\n",av[0]);return 2;}
    snprintf(pat,sizeof pat,"%s/chunks/*.tcap.zst",av[1]);
    if(glob(pat,0,NULL,&g)) fail("no chunks");
    for(size_t fi=0;fi<g.gl_pathc;fi++) {
        size_t cn; uint8_t *c=slurp(g.gl_pathv[fi],&cn), *raw; unsigned long long zn=ZSTD_getFrameContentSize(c,cn);
        if(zn==ZSTD_CONTENTSIZE_ERROR||zn==ZSTD_CONTENTSIZE_UNKNOWN) fail("bad zstd size");
        raw=malloc((size_t)zn); if(!raw) fail("oom");
        size_t got=ZSTD_decompress(raw,(size_t)zn,c,cn); free(c);
        if(ZSTD_isError(got)||got!=zn) fail("zstd decode failed");
        Reader r={raw,raw+got};
        if(memcmp(take(&r,8),"DSTCAP01",8)||ru32(&r)!=1) fail("bad capsule header");
        uint32_t bm=ru32(&r); (void)ru64(&r); uint32_t n=ru32(&r);
        if(!names){mode0=bm;nn=n;names=calloc(n,sizeof*names);for(uint32_t i=0;i<n;i++){uint16_t z=ru16(&r);names[i]=calloc(z+1,1);memcpy(names[i],take(&r,z),z);}}
        else {if(bm!=mode0||n!=nn)fail("chunk schema changed");for(uint32_t i=0;i<n;i++){uint16_t z=ru16(&r);if(strlen(names[i])!=z||memcmp(names[i],take(&r,z),z))fail("domain changed");}}
        while(r.p<r.end) {
            uint64_t local[10]={0};
            if(ru8(&r)!=1)fail("bad frame tag");
            (void)ru64(&r);(void)ru64(&r);uint32_t mf=ru32(&r);(void)ru32(&r);(void)ru32(&r);
            for(uint32_t i=0;i<nn;i++)(void)ru32(&r);
            for(int q=0;q<3;q++){
                uint32_t id=ru32(&r),sz=ru32(&r),runs=ru32(&r);const uint8_t*want_hash=take(&r,32);
                if(id<1||id>3)fail("bad domain id");
                if(!d[id].p){d[id].p=calloc(1,sz);d[id].n=sz;}if(d[id].n!=sz)fail("domain size changed");
                for(uint32_t j=0;j<runs;j++){uint32_t off=ru32(&r),len=ru32(&r);if((uint64_t)off+len>sz)fail("run overflow");memcpy(d[id].p+off,take(&r,len),len);}
                uint8_t hash[32];SHA256(d[id].p,sz,hash);if(memcmp(hash,want_hash,32))fail("domain hash mismatch");hashes++;
            }
            uint64_t bc=ru64(&r);
            for(uint64_t j=0;j<bc;j++){uint32_t pc=ru32(&r);uint64_t cnt=ru64(&r);wanted(pc,cnt,local);wanted(pc,cnt,totals);if(mf==349&&((pc>=0x8004abf4u&&pc<0x8004b6dcu)||(pc>=0x80058af8u&&pc<0x8005905cu)))printf("impact_block mf=%u pc=0x%08x count=%"PRIu64"\n",mf,pc,cnt);}
            uint32_t off=rd32(&d[1],0x800a655c);if(off)seed=0x8009fd80u+off;if(!seed)seed=0x800a07d0u;
            Actor cur[41];uint32_t table[40];for(unsigned i=0;i<41;i++)cur[i]=actor(&d[1],i);for(unsigned i=0;i<40;i++)table[i]=rd32(&d[1],0x80090748u+4u*i);
            if(!have_prev){
                puts("INITIAL_LIVE_TABLE");
                for(unsigned i=0;i<40;i++)if(valid_actor(table[i]))printf("slot=%u actor=0x%08x index=%d id=%u hp=%d kb=%d flags=0x%04x pos=(%d,%d,%d)\n",i,table[i],(int)((table[i]-0x8009fd80u)/0x84u)-1,rd32(&d[1],table[i]),rs16(&d[1],table[i]+0x6e),rs16(&d[1],table[i]+0x6c),rd16(&d[1],table[i]+0x5c),rs32(&d[1],table[i]+4),rs32(&d[1],table[i]+8),rs32(&d[1],table[i]+12));
                memcpy(prev,cur,sizeof prev);memcpy(prev_table,table,sizeof table);have_prev=1;
            } else {
                for(unsigned i=0;i<41;i++)if((cur[i].id||prev[i].id||member(&d[1],cur[i].ptr))&&(cur[i].knockback!=prev[i].knockback||cur[i].hp!=prev[i].hp||member(&d[1],cur[i].ptr)!=({int m=0;for(unsigned k=0;k<40;k++)if(prev_table[k]==cur[i].ptr)m=1;m;})))
                    printf("actor_event mf=%u actor=0x%08x index=%d id=%u hp=%d->%d kb=%d->%d live=%d flags=0x%04x pos=(%d,%d,%d)\n",mf,cur[i].ptr,(int)i-1,cur[i].id,prev[i].hp,cur[i].hp,prev[i].knockback,cur[i].knockback,member(&d[1],cur[i].ptr),cur[i].flags,rs32(&d[1],cur[i].ptr+4),rs32(&d[1],cur[i].ptr+8),rs32(&d[1],cur[i].ptr+12));
                for(unsigned i=0;i<40;i++)if(table[i]!=prev_table[i]&&(valid_actor(table[i])||valid_actor(prev_table[i])))printf("table_event mf=%u slot=%u 0x%08x->0x%08x\n",mf,i,prev_table[i],table[i]);
                memcpy(prev,cur,sizeof prev);memcpy(prev_table,table,sizeof table);
            }
            int any=0;for(unsigned i=0;i<10;i++)any|=local[i]!=0;
            if(any)printf("flow mf=%u dropped_guard=%"PRIu64" dropped_apply=%"PRIu64" sfx=%"PRIu64" burst=%"PRIu64" carried_kind=%"PRIu64" carried_flags=%"PRIu64" carried_sfx=%"PRIu64" carried_apply=%"PRIu64" retire_entry=%"PRIu64" retire_terminal=%"PRIu64"\n",mf,local[0],local[1],local[2],local[3],local[4],local[5],local[6],local[7],local[8],local[9]);
            if(mf==327||mf==329||(mf>=340&&mf<=372)||mf==400||mf==461){
                printf("seed mf=%u carry=0x%x mode=0x%02x actor=0x%08x id=%u hp=%d kb=%d live=%d flags=0x%04x pos=(%d,%d,%d) motion=(%d,%d,%d)\n",mf,off,rd8(&d[1],0x800a65a3),seed,rd32(&d[1],seed),rs16(&d[1],seed+0x6e),rs16(&d[1],seed+0x6c),member(&d[1],seed),rd16(&d[1],seed+0x5c),rs32(&d[1],seed+4),rs32(&d[1],seed+8),rs32(&d[1],seed+12),rs32(&d[1],seed+0x1c),rs32(&d[1],seed+0x20),rs32(&d[1],seed+0x24));
            }
            if(mf==347||mf==349||mf==351||mf==369||mf==387||mf==389||mf==391){uint32_t t=0x8009fd80u;printf("target mf=%u id=%u live=%d timer4a=%d react54=%d react56=%d react58=%d field5a=%d flags=0x%04x field62=%d kb=%d hp=%d vm=0x%08x\n",mf,rd32(&d[1],t),member(&d[1],t),rs16(&d[1],t+0x4a),rs16(&d[1],t+0x54),rs16(&d[1],t+0x56),rs16(&d[1],t+0x58),rs16(&d[1],t+0x5a),rd16(&d[1],t+0x5c),rs16(&d[1],t+0x62),rs16(&d[1],t+0x6c),rs16(&d[1],t+0x6e),rd32(&d[1],t+0x70));}
            frames++;
        }
        free(raw);
    }
    printf("SUMMARY chunks=%zu frames=%"PRIu64" hashes=%"PRIu64" all_hashes_ok=true mode=%u\n",g.gl_pathc,frames,hashes,mode0);
    printf("FLOW_TOTAL dropped_guard=%"PRIu64" dropped_apply=%"PRIu64" sfx=%"PRIu64" burst=%"PRIu64" carried_kind=%"PRIu64" carried_flags=%"PRIu64" carried_sfx=%"PRIu64" carried_apply=%"PRIu64" retire_entry=%"PRIu64" retire_terminal=%"PRIu64"\n",totals[0],totals[1],totals[2],totals[3],totals[4],totals[5],totals[6],totals[7],totals[8],totals[9]);
    globfree(&g);return 0;
}
