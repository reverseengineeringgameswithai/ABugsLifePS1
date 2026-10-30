#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define BASE 0x800b39a0u
static const char *rn[32]={"zero","at","v0","v1","a0","a1","a2","a3","t0","t1","t2","t3","t4","t5","t6","t7","s0","s1","s2","s3","s4","s5","s6","s7","t8","t9","k0","k1","gp","sp","fp","ra"};
typedef struct{uint8_t*p;size_t n;}Blob;
static uint32_t r32(const uint8_t*p){return(uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static Blob load(const char*p){FILE*f=fopen(p,"rb");Blob b={0};long n;if(!f){fprintf(stderr,"%s\n",strerror(errno));exit(2);}fseek(f,0,SEEK_END);n=ftell(f);fseek(f,0,SEEK_SET);b.n=(size_t)n;b.p=malloc(b.n);if(!b.p)exit(2);if(fread(b.p,1,b.n,f)!=b.n)exit(2);fclose(f);return b;}
static uint32_t jt(uint32_t pc,uint32_t w){return((pc+4)&0xf0000000u)|((w&0x3ffffffu)<<2);}
static void di(uint32_t pc,uint32_t w){
 unsigned op=w>>26,rs=(w>>21)&31,rt=(w>>16)&31,rd=(w>>11)&31,sa=(w>>6)&31,fn=w&63;int16_t im=(int16_t)w;
 printf("0x%08"PRIx32"  0x%08"PRIx32"  ",pc,w);
 if(!w)printf("nop");
 else if(op==0)switch(fn){
  case 0:printf("sll $%s,$%s,%u",rn[rd],rn[rt],sa);break;case 2:printf("srl $%s,$%s,%u",rn[rd],rn[rt],sa);break;
  case 3:printf("sra $%s,$%s,%u",rn[rd],rn[rt],sa);break;case 8:printf("jr $%s",rn[rs]);break;
  case 9:printf("jalr $%s,$%s",rn[rd],rn[rs]);break;case 0x10:printf("mfhi $%s",rn[rd]);break;case 0x12:printf("mflo $%s",rn[rd]);break;
  case 0x18:printf("mult $%s,$%s",rn[rs],rn[rt]);break;case 0x19:printf("multu $%s,$%s",rn[rs],rn[rt]);break;
  case 0x21:printf("addu $%s,$%s,$%s",rn[rd],rn[rs],rn[rt]);break;case 0x23:printf("subu $%s,$%s,$%s",rn[rd],rn[rs],rn[rt]);break;
  case 0x24:printf("and $%s,$%s,$%s",rn[rd],rn[rs],rn[rt]);break;case 0x25:printf("or $%s,$%s,$%s",rn[rd],rn[rs],rn[rt]);break;
  case 0x2a:printf("slt $%s,$%s,$%s",rn[rd],rn[rs],rn[rt]);break;case 0x2b:printf("sltu $%s,$%s,$%s",rn[rd],rn[rs],rn[rt]);break;
  default:printf("special_%02x",fn);
 }else if(op==2)printf("j 0x%08"PRIx32,jt(pc,w));else if(op==3)printf("jal 0x%08"PRIx32,jt(pc,w));
 else if(op==1)printf("%s $%s,0x%08"PRIx32,rt==0?"bltz":rt==1?"bgez":"regimm",rn[rs],pc+4+((int32_t)im<<2));
 else if(op==4)printf("beq $%s,$%s,0x%08"PRIx32,rn[rs],rn[rt],pc+4+((int32_t)im<<2));
 else if(op==5)printf("bne $%s,$%s,0x%08"PRIx32,rn[rs],rn[rt],pc+4+((int32_t)im<<2));
 else if(op==6)printf("blez $%s,0x%08"PRIx32,rn[rs],pc+4+((int32_t)im<<2));
 else if(op==7)printf("bgtz $%s,0x%08"PRIx32,rn[rs],pc+4+((int32_t)im<<2));
 else if(op==9)printf("addiu $%s,$%s,%d",rn[rt],rn[rs],im);else if(op==10)printf("slti $%s,$%s,%d",rn[rt],rn[rs],im);
 else if(op==11)printf("sltiu $%s,$%s,%d",rn[rt],rn[rs],im);else if(op==12)printf("andi $%s,$%s,0x%x",rn[rt],rn[rs],w&0xffff);
 else if(op==13)printf("ori $%s,$%s,0x%x",rn[rt],rn[rs],w&0xffff);else if(op==15)printf("lui $%s,0x%x",rn[rt],w&0xffff);
 else {const char*m=op==0x20?"lb":op==0x21?"lh":op==0x23?"lw":op==0x24?"lbu":op==0x25?"lhu":op==0x28?"sb":op==0x29?"sh":op==0x2b?"sw":NULL;
  if(m)printf("%s $%s,%d($%s)",m,rn[rt],im,rn[rs]);else printf("op_%02x",op);
 }
 putchar('\n');
}
static void one(const char*path,uint32_t start){
 Blob b=load(path);printf("\n## %s @ 0x%08"PRIx32"\n",path,start);
 for(uint32_t pc=start;(size_t)(pc-BASE)+4<=b.n;pc+=4){uint32_t w=r32(b.p+(pc-BASE));di(pc,w);if(w==0x03e00008u){pc+=4;if((size_t)(pc-BASE)+4<=b.n)di(pc,r32(b.p+(pc-BASE)));break;}}
 free(b.p);
}
int main(void){one("REBUILD/files/LEVEL03/LEVEL.BIN",0x800b3d78u);one("REBUILD/files/LEVEL07/LEVEL1.BIN",0x800b3f00u);return 0;}
