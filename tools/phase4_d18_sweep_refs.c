#include <inttypes.h>
#include <openssl/evp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define COUNTER_PC 0x800B3DB0u
#define COUNTER_WORD 0xAC224CC8u
#define RESTORE_PC 0x800B3ED0u
#define RESTORE_WORD 0xA662006Eu
#define SWEEP_LOW 0x4CB0u
#define RETAIL_OVERLAY_SHA256 "816667f0ba7ae2b602cc39da7c0b3b4020d1a231651d5b90e6374c66c34f39e6"
static uint32_t le32(const uint8_t*p){return(uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static const char*opname(unsigned op){switch(op){case 0x20:return"lb";case 0x21:return"lh";case 0x23:return"lw";case 0x24:return"lbu";case 0x25:return"lhu";case 0x28:return"sb";case 0x29:return"sh";case 0x2b:return"sw";default:return NULL;}}
static void hash(const uint8_t*p,size_t n,char out[65]){EVP_MD_CTX*c=EVP_MD_CTX_new();uint8_t d[32];unsigned z=0;size_t i;if(!c||EVP_DigestInit_ex(c,EVP_sha256(),NULL)!=1||EVP_DigestUpdate(c,p,n)!=1||EVP_DigestFinal_ex(c,d,&z)!=1||z!=32){fprintf(stderr,"sha\n");exit(2);}EVP_MD_CTX_free(c);for(i=0;i<32;i++)sprintf(out+i*2,"%02x",d[i]);out[64]=0;}
int main(int argc,char**argv){FILE*f;long n,o,hit=-1,restore=-1;uint8_t*b;unsigned hc=0,rc=0,refs=0;uint32_t base;char sha[65];if(argc!=3){fprintf(stderr,"usage: %s LEVEL1.BIN OUT.json\n",argv[0]);return 2;}f=fopen(argv[1],"rb");if(!f){perror(argv[1]);return 2;}fseek(f,0,SEEK_END);n=ftell(f);rewind(f);b=malloc((size_t)n);if(!b||fread(b,1,(size_t)n,f)!=(size_t)n)return 2;fclose(f);hash(b,(size_t)n,sha);if(strcmp(sha,RETAIL_OVERLAY_SHA256)){fprintf(stderr,"overlay hash mismatch\n");return 1;}for(o=0;o+4<=n;o+=4){uint32_t w=le32(b+o);if(w==COUNTER_WORD){hit=o;hc++;}if(w==RESTORE_WORD){restore=o;rc++;}}if(hc!=1||rc!=1){fprintf(stderr,"anchor multiplicity %u/%u\n",hc,rc);return 1;}base=COUNTER_PC-(uint32_t)hit;if(base+(uint32_t)restore!=RESTORE_PC){fprintf(stderr,"base mismatch\n");return 1;}for(o=0;o+4<=n;o+=4){uint32_t w=le32(b+o);const char*name=opname(w>>26);if(name&&(w&0xffff)==SWEEP_LOW)refs++;}if(refs!=7){fprintf(stderr,"unexpected sweep reference count %u\n",refs);return 1;}f=fopen(argv[2],"w");if(!f)return 2;fprintf(f,"{\n \"schema\":\"phase4-d18-sweep-ref-census-v1\",\n \"overlay\":\"%s\",\n \"overlay_sha256\":\"%s\",\n \"size\":%ld,\n \"load_base\":\"0x%08" PRIx32 "\",\n \"target\":\"0x800B4CB0\",\n \"references\":[\n",argv[1],sha,n,base);refs=0;for(o=0;o+4<=n;o+=4){uint32_t w=le32(b+o);unsigned op=w>>26,rs=(w>>21)&31,rt=(w>>16)&31,imm=w&0xffff;const char*name=opname(op);if(name&&imm==SWEEP_LOW){long p0=o>=8?o-8:0,p1=o+8<n?o+8:n-4;fprintf(f,"  {\"pc\":\"0x%08" PRIx32 "\",\"word\":\"0x%08" PRIx32 "\",\"op\":\"%s\",\"rs\":%u,\"rt\":%u,\"context\":[",base+(uint32_t)o,w,name,rs,rt);for(long p=p0;p<=p1;p+=4)fprintf(f,"\"0x%08" PRIx32 "\"%s",le32(b+p),p==p1?"":",");refs++;fprintf(f,"]}%s\n",refs==7?"":",");}}
fprintf(f," ],\n \"reference_count\":%u,\n \"writers\":[\"0x800B3B40\",\"0x800B4388\",\"0x800B43A8\"],\n \"step\":2560,\n \"published_actor_field\":\"+0x28\",\n \"result\":\"D18_SWEEP_REFERENCE_CENSUS_PASS\"\n}\n",refs);fclose(f);printf("D18_SWEEP_REF_CENSUS PASS: base=0x%08" PRIx32 " size=%ld refs=%u sha=%s\n",base,n,refs,sha);free(b);return 0;}
