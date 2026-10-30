#include <inttypes.h>
#include <openssl/sha.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *rn[32]={"zero","at","v0","v1","a0","a1","a2","a3","t0","t1","t2","t3","t4","t5","t6","t7","s0","s1","s2","s3","s4","s5","s6","s7","t8","t9","k0","k1","gp","sp","fp","ra"};
static uint32_t le32(const uint8_t *p){return p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static uint8_t *slurp(const char *p,size_t *n){FILE*f=fopen(p,"rb");long z;uint8_t*b;if(!f){perror(p);exit(2);}fseek(f,0,SEEK_END);z=ftell(f);rewind(f);b=malloc((size_t)z);if(!b||fread(b,1,(size_t)z,f)!=(size_t)z){fputs("read failed\n",stderr);exit(2);}fclose(f);*n=(size_t)z;return b;}
static void hex32(const uint8_t*h){for(int i=0;i<32;i++)printf("%02x",h[i]);}
static const char *memop(unsigned op){switch(op){case 0x20:return"lb";case 0x21:return"lh";case 0x23:return"lw";case 0x24:return"lbu";case 0x25:return"lhu";case 0x28:return"sb";case 0x29:return"sh";case 0x2b:return"sw";default:return NULL;}}
static void decode(uint32_t pc,uint32_t w){unsigned op=w>>26,rs=w>>21&31,rt=w>>16&31,rd=w>>11&31,fn=w&63;int16_t im=(int16_t)w;const char*m;
 if(w==0){printf("nop");return;}if(op==0){if(fn==8)printf("jr $%s",rn[rs]);else if(fn==0x21)printf("addu $%s,$%s,$%s",rn[rd],rn[rs],rn[rt]);else printf("special fn=0x%x",fn);return;}
 if(op==2||op==3){uint32_t t=((pc+4)&0xf0000000u)|((w&0x03ffffffu)<<2);printf("%s 0x%08x",op==3?"jal":"j",t);return;}
 if(op>=4&&op<=7){static const char*n[]={"beq","bne","blez","bgtz"};uint32_t t=pc+4+((int32_t)im<<2);if(op<=5)printf("%s $%s,$%s,0x%08x",n[op-4],rn[rs],rn[rt],t);else printf("%s $%s,0x%08x",n[op-4],rn[rs],t);return;}
 if(op==9){printf("addiu $%s,$%s,%d",rn[rt],rn[rs],im);return;}if(op==0xb){printf("sltiu $%s,$%s,%d",rn[rt],rn[rs],im);return;}if(op==0xc||op==0xd){printf("%s $%s,$%s,0x%x",op==0xc?"andi":"ori",rn[rt],rn[rs],(uint16_t)im);return;}if(op==0xf){printf("lui $%s,0x%x",rn[rt],(uint16_t)im);return;}
 if((m=memop(op))){printf("%s $%s,%d($%s)",m,rn[rt],im,rn[rs]);return;}printf("op=0x%x",op);
}
static uint32_t word_at(const uint8_t*b,size_t n,uint32_t load,uint32_t pc){uint64_t o=0x800ull+(uint64_t)pc-load;if(o+4>n){fprintf(stderr,"address 0x%08x outside EXE\n",pc);exit(3);}return le32(b+o);}
static void dump(const uint8_t*b,size_t n,uint32_t load,uint32_t a,uint32_t z){for(uint32_t pc=a;pc<=z;pc+=4){uint32_t w=word_at(b,n,load,pc);printf("0x%08x  %08x  ",pc,w);decode(pc,w);putchar('\n');}}
int main(int ac,char**av){size_t n;uint8_t*b,h[32];if(ac!=2){fprintf(stderr,"usage: %s PSX_EXE\n",av[0]);return 2;}b=slurp(av[1],&n);if(n<0x800||memcmp(b,"PS-X EXE",8)){fputs("not PS-X EXE\n",stderr);return 3;}uint32_t load=le32(b+0x18),sz=le32(b+0x1c);SHA256(b,n,h);printf("file=%s bytes=%zu sha256=",av[1],n);hex32(h);printf(" load=0x%08x payload=%u\n",load,sz);
 puts("CARRIED_CONTACT_ARM");dump(b,n,load,0x80058de4u,0x80058e38u);puts("DROPPED_CONTACT_ARM");dump(b,n,load,0x8004b290u,0x8004b2e4u);
 puts("NEGATIVE_20_TO_ACTOR_6C_WRITERS");unsigned found=0,hpstores=0;for(uint32_t pc=load;pc+4<load+sz;pc+=4){uint32_t w=word_at(b,n,load,pc);unsigned op=w>>26,rt=w>>16&31,rs=w>>21&31;int16_t im=(int16_t)w;if(op==0x29&&im==0x6e)hpstores++;if(op!=9||rs!=0||im!=-20)continue;for(unsigned k=1;k<=6;k++){uint32_t q=word_at(b,n,load,pc+4*k);if((q>>26)==0x29&&(q>>16&31)==rt&&(int16_t)q==0x6c){printf("constant_pc=0x%08x store_pc=0x%08x register=$%s\n",pc,pc+4*k,rn[rt]);found++;}}}
 printf("SUMMARY negative20_actor6c_writers=%u actor_hp_store_sites=%u\n",found,hpstores);free(b);return 0;}
