#define _POSIX_C_SOURCE 200809L
#include <dirent.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint32_t word_at(const uint8_t *p) { uint32_t v; memcpy(&v,p,4); return v; }
static int direct_target(uint32_t w, uint16_t imm) {
    unsigned op=w>>26, base=(w>>21)&31;
    return (op==0x20||op==0x21||op==0x23||op==0x24||op==0x25||op==0x28||op==0x29||op==0x2b) &&
           base==1 && (uint16_t)w==imm;
}
static void scan(const char *path) {
    FILE *f=fopen(path,"rb"); if(!f)return; fseek(f,0,SEEK_END); long n=ftell(f); rewind(f);
    uint8_t *b=malloc((size_t)n); if(!b||fread(b,1,(size_t)n,f)!=(size_t)n){fclose(f);free(b);return;} fclose(f);
    int hits=0;
    for(long o=0;o+4<=n;o+=4) {
        uint32_t w=word_at(b+o); uint16_t targets[]={0x65a3,0x655c,0x6580,0x6582};
        for(size_t t=0;t<sizeof(targets)/sizeof(targets[0]);t++) if(direct_target(w,targets[t])) {
            int has_lui=0; for(long q=o-32;q<o;q+=4) if(q>=0 && word_at(b+q)==0x3c01800a)has_lui=1;
            if(!has_lui)continue; if(!hits++)printf("=== %s bytes=%ld ===\n",path,n);
            printf("offset=0x%06lx target=0x800a%04x word=0x%08x\n",o,targets[t],w);
            long lo=o>=24?o-24:0,hi=o+28<n?o+28:n;
            for(long q=lo;q<hi;q+=4)printf("  %c +0x%06lx 0x%08x\n",q==o?'>':' ',q,word_at(b+q));
        }
    }
    free(b);
}
int main(void) {
    char path[512];
    for(int level=1;level<=15;level++) {
        snprintf(path,sizeof(path),"REBUILD/files/LEVEL%02d/LEVEL.BIN",level); scan(path);
    }
    return 0;
}
