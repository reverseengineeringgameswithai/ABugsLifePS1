/* Phase 4 D18: fail-closed native berry -> Thud damage closure. */
#include <inttypes.h>
#include <openssl/evp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define RETAIL_SHA256 "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20"
#define METADATA_BASE 0x8007941cu
#define METADATA_STRIDE 0x14u

struct executable { uint8_t *data; size_t size; uint32_t load, text_size; };
struct anchor { uint32_t address, word; const char *name; };
struct variant { const char *name; unsigned equip; unsigned type; unsigned connection; unsigned selector; unsigned expected_delta; int berry_tough_blocked; };

static void fail(const char *s) { fprintf(stderr, "phase4_d18_native_berry_closure: %s\n", s); exit(1); }
static uint16_t le16(const uint8_t *p) { return (uint16_t)(p[0] | ((uint16_t)p[1] << 8)); }
static uint32_t le32(const uint8_t *p) { return (uint32_t)le16(p) | ((uint32_t)le16(p + 2) << 16); }
static struct executable load_exe(const char *path) {
    struct executable x = {0}; FILE *f = fopen(path, "rb"); long n;
    if (!f || fseek(f,0,SEEK_END) || (n=ftell(f)) < 0 || fseek(f,0,SEEK_SET)) fail("cannot open executable");
    x.size=(size_t)n; x.data=malloc(x.size ? x.size : 1);
    if (!x.data || fread(x.data,1,x.size,f)!=x.size) fail("cannot read executable");
    fclose(f); if (x.size<0x800 || memcmp(x.data,"PS-X EXE",8)) fail("not a PS-X EXE");
    x.load=le32(x.data+0x18); x.text_size=le32(x.data+0x1c); return x;
}
static const uint8_t *ptr(const struct executable *x, uint32_t a, size_t n) {
    uint64_t d; if (a < x->load) fail("address before load"); d=(uint64_t)a-x->load;
    if (d+n>x->text_size || 0x800+d+n>x->size) fail("address outside executable");
    return x->data+0x800+(size_t)d;
}
static uint32_t word(const struct executable *x, uint32_t a) { return le32(ptr(x,a,4)); }
static void sha256(const uint8_t *p,size_t n,char out[65]) {
    EVP_MD_CTX *c=EVP_MD_CTX_new(); uint8_t d[32]; unsigned dn=0; size_t i;
    if(!c || EVP_DigestInit_ex(c,EVP_sha256(),NULL)!=1 || EVP_DigestUpdate(c,p,n)!=1 || EVP_DigestFinal_ex(c,d,&dn)!=1 || dn!=32) fail("SHA-256 failure");
    EVP_MD_CTX_free(c); for(i=0;i<32;i++) sprintf(out+i*2,"%02x",d[i]); out[64]=0;
}
static unsigned selector_delta(unsigned selector) {
    if (selector == 0 || selector == 12) return 2;
    if (selector == 1) return 99;
    if (selector == 127) return 4;
    if (selector == 128) return 3;
    return 1;
}
int main(int argc,char **argv) {
    static const struct anchor anchors[] = {
      {0x800471a4,0x24110002,"red type 2"}, {0x800471b0,0x24110005,"blue type 5"},
      {0x800471b8,0x24110008,"green type 8"}, {0x800471c4,0x2411000b,"gold type 11"},
      {0x800471c8,0x2411002d,"mega type 45"}, {0x80047228,0xafb1001c,"constructor type argument"},
      {0x8005751c,0x24020030,"mega child type 48"}, {0x80057560,0x24020010,"green child type 16"},
      {0x8005a268,0x90a20011,"metadata selector load"}, {0x8005a270,0xa2020034,"contact selector store"},
      {0x80058ee4,0x30420040,"berry-tough flag test"}, {0x80058ee8,0x1040005c,"ordinary branch"},
      {0x80058ef0,0x86220024,"biased connection-class load"}, {0x80059068,0x28420064,"HP below 100 gate"},
      {0x80059074,0x9223002c,"contact selector read"}, {0x80059098,0x2482ff9d,"selector 1 minus 99"},
      {0x800590b4,0x2482fffd,"selector 128 minus 3"}, {0x800590c4,0x2482fffe,"selector 0 minus 2"},
      {0x800590cc,0x2482fffe,"selector 12 minus 2"}, {0x800590d4,0x2482fffc,"selector 127 minus 4"},
      {0x800590e0,0x2442ffff,"default minus 1"}, {0x800590e4,0xa642006e,"actor latch store"}
    };
    static const struct variant variants[] = {
      {"red_primary",0,2,1,112,0,1}, {"blue_primary",1,5,2,0,2,0},
      {"green_primary",2,8,5,12,2,0}, {"green_child",2,16,3,12,2,0},
      {"gold_primary",3,11,4,127,4,0}, {"mega_primary",4,45,9,128,3,0},
      {"mega_child",4,48,8,128,3,0}
    };
    struct executable x; char hash[65]; size_t i; unsigned max=0, softlock=0, instant=0;
    if(argc!=3){fprintf(stderr,"usage: %s SCUS_942.88 OUT.json\n",argv[0]);return 2;}
    x=load_exe(argv[1]); sha256(x.data,x.size,hash); if(strcmp(hash,RETAIL_SHA256)) fail("pristine hash mismatch");
    for(i=0;i<sizeof(anchors)/sizeof(anchors[0]);i++) if(word(&x,anchors[i].address)!=anchors[i].word){fprintf(stderr,"anchor mismatch 0x%08" PRIx32 " %s\n",anchors[i].address,anchors[i].name);return 1;}
    for(i=0;i<sizeof(variants)/sizeof(variants[0]);i++) {
      const uint8_t *row=ptr(&x,METADATA_BASE+variants[i].type*METADATA_STRIDE,METADATA_STRIDE);
      unsigned connection=le16(row+0x0c), selector=row[0x11], delta=selector_delta(selector);
      if(connection!=variants[i].connection || selector!=variants[i].selector || (!variants[i].berry_tough_blocked && delta!=variants[i].expected_delta)) fail("metadata or damage mapping mismatch");
      if(!variants[i].berry_tough_blocked){if(delta>max)max=delta;if(delta>=30&&delta<=49)softlock++;if(delta>=50)instant++;}
    }
    if(max!=4 || softlock || instant) fail("native berry reachability invariant failed");
    FILE *o=fopen(argv[2],"w"); if(!o) fail("cannot open output");
    fprintf(o,"{\n  \"schema\": \"phase4-d18-native-berry-closure-v1\",\n  \"row\": \"D18_thud\",\n  \"status\": \"substantiated_partial_bounded_exhausted\",\n  \"pristine_exe_sha256\": \"%s\",\n  \"anchors_checked\": %zu,\n  \"metadata_rows_checked\": %zu,\n  \"variants\": [\n",hash,sizeof(anchors)/sizeof(anchors[0]),sizeof(variants)/sizeof(variants[0]));
    for(i=0;i<sizeof(variants)/sizeof(variants[0]);i++) {
      unsigned raw=selector_delta(variants[i].selector), effective=variants[i].berry_tough_blocked?0:raw;
      fprintf(o,"    {\"name\":\"%s\",\"equip_index\":%u,\"constructor_type\":%u,\"connection_class\":%u,\"damage_selector\":%u,\"dispatcher_delta\":%u,\"berry_tough_blocked\":%s,\"effective_thud_delta\":%u}%s\n",variants[i].name,variants[i].equip,variants[i].type,variants[i].connection,variants[i].selector,raw,variants[i].berry_tough_blocked?"true":"false",effective,(i+1==sizeof(variants)/sizeof(variants[0]))?"":",");
    }
    fprintf(o,"  ],\n  \"native_effective_damage_set\": [0,2,3,4],\n  \"native_max_effective_damage\": %u,\n  \"softlock_band_30_49_reachable\": false,\n  \"instant_retire_band_ge_50_reachable\": false,\n  \"selector_1_minus_99_native_reachable\": false,\n  \"mega_category_correction\": \"constructor type 45 indexes metadata; the copied damage selector is 128 and dispatches to minus 3\",\n  \"softlock_classification\": \"perturbation_only_not_native_gameplay\",\n  \"interpreter_movie_required\": false,\n  \"result\": \"D18_NATIVE_BERRY_CLOSURE_PASS\"\n}\n",max);
    fclose(o); free(x.data);
    printf("D18_NATIVE_BERRY_CLOSURE PASS: anchors=%zu rows=%zu native_max=%u softlock_band=unreachable movie_required=false\n",sizeof(anchors)/sizeof(anchors[0]),sizeof(variants)/sizeof(variants[0]),max);
    return 0;
}
