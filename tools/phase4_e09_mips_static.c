#define _POSIX_C_SOURCE 200809L
#include <glob.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { RAM_SIZE=0x200000 };
static const char *rn[32]={"zero","at","v0","v1","a0","a1","a2","a3","t0","t1","t2","t3","t4","t5","t6","t7","s0","s1","s2","s3","s4","s5","s6","s7","t8","t9","k0","k1","gp","sp","fp","ra"};
static uint32_t ld32(const uint8_t*p){return(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static void decode(uint32_t pc,uint32_t w,char*out,size_t n){
 unsigned op=w>>26,rs=w>>21&31,rt=w>>16&31,rd=w>>11&31,sa=w>>6&31,fn=w&63;int16_t im=(int16_t)w;uint32_t target=(pc+4&0xf0000000)|((w&0x3ffffff)<<2);
 if(!w)snprintf(out,n,"nop");
 else if(op==0&&fn==8)snprintf(out,n,"jr %s",rn[rs]);
 else if(op==0&&fn==9)snprintf(out,n,"jalr %s,%s",rn[rd],rn[rs]);
 else if(op==0&&fn==33)snprintf(out,n,"addu %s,%s,%s",rn[rd],rn[rs],rn[rt]);
 else if(op==0&&fn==35)snprintf(out,n,"subu %s,%s,%s",rn[rd],rn[rs],rn[rt]);
 else if(op==0&&fn==42)snprintf(out,n,"slt %s,%s,%s",rn[rd],rn[rs],rn[rt]);
 else if(op==0&&fn==0)snprintf(out,n,"sll %s,%s,%u",rn[rd],rn[rt],sa);
 else if(op==0&&fn==2)snprintf(out,n,"srl %s,%s,%u",rn[rd],rn[rt],sa);
 else if(op==0&&fn==3)snprintf(out,n,"sra %s,%s,%u",rn[rd],rn[rt],sa);
 else if(op==2)snprintf(out,n,"j 0x%08x",target);
 else if(op==3)snprintf(out,n,"jal 0x%08x",target);
 else if(op==4)snprintf(out,n,"beq %s,%s,0x%08x",rn[rs],rn[rt],pc+4+(int32_t)im*4);
 else if(op==5)snprintf(out,n,"bne %s,%s,0x%08x",rn[rs],rn[rt],pc+4+(int32_t)im*4);
 else if(op==6)snprintf(out,n,"blez %s,0x%08x",rn[rs],pc+4+(int32_t)im*4);
 else if(op==7)snprintf(out,n,"bgtz %s,0x%08x",rn[rs],pc+4+(int32_t)im*4);
 else if(op==8||op==9)snprintf(out,n,"addiu %s,%s,%d",rn[rt],rn[rs],im);
 else if(op==10)snprintf(out,n,"slti %s,%s,%d",rn[rt],rn[rs],im);
 else if(op==11)snprintf(out,n,"sltiu %s,%s,%d",rn[rt],rn[rs],im);
 else if(op==12)snprintf(out,n,"andi %s,%s,0x%04x",rn[rt],rn[rs],w&0xffff);
 else if(op==13)snprintf(out,n,"ori %s,%s,0x%04x",rn[rt],rn[rs],w&0xffff);
 else if(op==15)snprintf(out,n,"lui %s,0x%04x",rn[rt],w&0xffff);
 else if(op==32)snprintf(out,n,"lb %s,%d(%s)",rn[rt],im,rn[rs]);
 else if(op==33)snprintf(out,n,"lh %s,%d(%s)",rn[rt],im,rn[rs]);
 else if(op==35)snprintf(out,n,"lw %s,%d(%s)",rn[rt],im,rn[rs]);
 else if(op==36)snprintf(out,n,"lbu %s,%d(%s)",rn[rt],im,rn[rs]);
 else if(op==37)snprintf(out,n,"lhu %s,%d(%s)",rn[rt],im,rn[rs]);
 else if(op==40)snprintf(out,n,"sb %s,%d(%s)",rn[rt],im,rn[rs]);
 else if(op==41)snprintf(out,n,"sh %s,%d(%s)",rn[rt],im,rn[rs]);
 else if(op==43)snprintf(out,n,"sw %s,%d(%s)",rn[rt],im,rn[rs]);
 else snprintf(out,n,".word 0x%08x",w);
}
static int code_off(uint32_t o){return(o>=0x10000&&o<0x90000)||(o>=0xb0000&&o<0xc0000);}
static void window(const uint8_t*ram,uint32_t center,unsigned before,unsigned after){
 uint32_t lo=center>before*4?center-before*4:0,hi=center+after*4;if(hi>RAM_SIZE-4)hi=RAM_SIZE-4;
 for(uint32_t o=lo;o<=hi;o+=4){char s[128];uint32_t pc=0x80000000u+o,w=ld32(ram+o);decode(pc,w,s,sizeof(s));printf("      %c 0x%08x  0x%08x  %s\n",o==center?'*':' ',pc,w,s);}
}
static void analyze(const char*path){
 FILE*f=fopen(path,"rb");if(!f){perror(path);exit(2);}uint8_t*ram=malloc(RAM_SIZE);if(!ram)exit(2);if(fread(ram,1,RAM_SIZE,f)!=RAM_SIZE){fprintf(stderr,"short RAM: %s\n",path);exit(2);}fclose(f);
 const char*b=strrchr(path,'/');b=b?b+1:path;printf("CAPSULE %s\n",b);unsigned refs=0;
 for(uint32_t o=0;o<RAM_SIZE-4;o+=4){if(!code_off(o))continue;uint32_t w=ld32(ram+o),op=w>>26,imm=w&0xffff;
   int hit=(op==3&&(((w&0x3ffffff)<<2)|0x80000000u)==0x80029030u)||((op==8||op==9||op==10||op==11||op==12||op==13)&&(imm==0x10c7||imm==0x1068||imm==0xff74||imm==0x0690));
   if(hit){char s[128];decode(0x80000000u+o,w,s,sizeof(s));printf("  MATCH 0x%08x  %s\n",0x80000000u+o,s);refs++;}
 }
 for(uint32_t o=0;o<RAM_SIZE-4*24;o+=4){if(!code_off(o))continue;uint32_t w=ld32(ram+o);if((w>>26)!=15||(w&0xffff)!=0x800a)continue;unsigned base=w>>16&31;
   for(unsigned k=1;k<=24;k++){uint32_t x=ld32(ram+o+k*4),op=x>>26,rs=x>>21&31;if(op==36&&rs==base&&(x&0xffff)==0x65a1){printf("  GRAIN_REF lui=0x%08x load=0x%08x\n",0x80000000u+o,0x80000000u+o+k*4);window(ram,o,4,k+8);refs++;break;}}
 }
 printf("  SUMMARY matches=%u\n",refs);free(ram);
}
int main(int argc,char**argv){
 if(argc==4&&!strcmp(argv[1],"--xref")){
  FILE*f=fopen(argv[2],"rb");if(!f){perror(argv[2]);return 2;}uint8_t*ram=malloc(RAM_SIZE);if(!ram)return 2;if(fread(ram,1,RAM_SIZE,f)!=RAM_SIZE)return 2;fclose(f);uint32_t target=(uint32_t)strtoul(argv[3],NULL,0),high=target>>16,low=target&0xffff;
  for(uint32_t o=0;o<RAM_SIZE-4*24;o+=4){uint32_t w=ld32(ram+o);if((w>>26)!=15||(w&0xffff)!=high)continue;unsigned base=w>>16&31;for(unsigned k=1;k<=24;k++){uint32_t x=ld32(ram+o+k*4),op=x>>26,rs=x>>21&31;if(rs==base&&(x&0xffff)==low&&(op==32||op==33||op==35||op==36||op==37||op==40||op==41||op==43)){printf("XREF target=0x%08x lui=0x%08x access=0x%08x\n",target,0x80000000u+o,0x80000000u+o+k*4);window(ram,o,3,k+5);break;}}}
  free(ram);return 0;
 }
 if(argc==5&&!strcmp(argv[1],"--window")){
  FILE*f=fopen(argv[2],"rb");if(!f){perror(argv[2]);return 2;}uint8_t*ram=malloc(RAM_SIZE);if(!ram)return 2;if(fread(ram,1,RAM_SIZE,f)!=RAM_SIZE)return 2;fclose(f);
  uint32_t lo=(uint32_t)strtoul(argv[3],NULL,0)&0x1fffffff,hi=(uint32_t)strtoul(argv[4],NULL,0)&0x1fffffff;
  for(uint32_t o=lo;o<=hi;o+=4){char s[128];uint32_t pc=0x80000000u+o,w=ld32(ram+o);decode(pc,w,s,sizeof(s));printf("0x%08x  0x%08x  %s\n",pc,w,s);}free(ram);return 0;
 }
 if(argc!=2){fprintf(stderr,"usage: %s RAM_DUMP_GLOB | --window RAM START END | --xref RAM TARGET\n",argv[0]);return 2;}glob_t g={0};if(glob(argv[1],0,NULL,&g)||!g.gl_pathc){fprintf(stderr,"no RAM dumps\n");return 2;}for(size_t i=0;i<g.gl_pathc;i++)analyze(g.gl_pathv[i]);globfree(&g);return 0;
}
