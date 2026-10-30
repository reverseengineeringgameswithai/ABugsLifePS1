#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { uint8_t *p; size_t n; uint32_t load; } Exe;
static uint32_t le32(const uint8_t *p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static Exe load_exe(const char *path){
  FILE *f=fopen(path,"rb");Exe e={0};long n;if(!f){fprintf(stderr,"%s: %s\n",path,strerror(errno));exit(2);}
  if(fseek(f,0,SEEK_END)||(n=ftell(f))<0||fseek(f,0,SEEK_SET))exit(2);
  e.n=(size_t)n;e.p=malloc(e.n);if(!e.p||fread(e.p,1,e.n,f)!=e.n)exit(2);fclose(f);
  if(e.n<0x800||memcmp(e.p,"PS-X EXE",8))exit(2);
  e.load=le32(e.p+0x18);
  return e;
}
static size_t off(const Exe *e,uint32_t va){return 0x800u+(size_t)(va-e->load);}
static uint32_t word(const Exe *e,uint32_t va){size_t o=off(e,va);return o+4<=e->n?le32(e->p+o):0;}
static const char *rn(unsigned r){static const char *n[]={"zero","at","v0","v1","a0","a1","a2","a3","t0","t1","t2","t3","t4","t5","t6","t7","s0","s1","s2","s3","s4","s5","s6","s7","t8","t9","k0","k1","gp","sp","fp","ra"};return n[r&31];}
static void decode(uint32_t pc,uint32_t w,char *b,size_t n){
  unsigned op=w>>26,rs=(w>>21)&31,rt=(w>>16)&31,rd=(w>>11)&31,fn=w&63;int16_t si=(int16_t)w;uint16_t ui=(uint16_t)w;
  uint32_t bt=pc+4+((int32_t)si<<2),jt=((pc+4)&0xf0000000)|((w&0x03ffffff)<<2);
  if(!w){snprintf(b,n,"nop");return;}
  if(op==0){
    if(fn==0x21)snprintf(b,n,"addu %s,%s,%s",rn(rd),rn(rs),rn(rt));
    else if(fn==0x23)snprintf(b,n,"subu %s,%s,%s",rn(rd),rn(rs),rn(rt));
    else if(fn==0x24)snprintf(b,n,"and %s,%s,%s",rn(rd),rn(rs),rn(rt));
    else if(fn==0x25)snprintf(b,n,"or %s,%s,%s",rn(rd),rn(rs),rn(rt));
    else if(fn==0x2a)snprintf(b,n,"slt %s,%s,%s",rn(rd),rn(rs),rn(rt));
    else if(fn==8)snprintf(b,n,"jr %s",rn(rs));
    else if(fn==9)snprintf(b,n,"jalr %s,%s",rn(rd),rn(rs));
    else if(fn==0)snprintf(b,n,"sll %s,%s,%u",rn(rd),rn(rt),(w>>6)&31);
    else if(fn==2)snprintf(b,n,"srl %s,%s,%u",rn(rd),rn(rt),(w>>6)&31);
    else if(fn==3)snprintf(b,n,"sra %s,%s,%u",rn(rd),rn(rt),(w>>6)&31);
    else snprintf(b,n,"SPECIAL fn=0x%x",fn);
    return;
  }
  switch(op){
    case 2:snprintf(b,n,"j 0x%08"PRIx32,jt);break;case 3:snprintf(b,n,"jal 0x%08"PRIx32,jt);break;
    case 4:snprintf(b,n,"beq %s,%s,0x%08"PRIx32,rn(rs),rn(rt),bt);break;
    case 5:snprintf(b,n,"bne %s,%s,0x%08"PRIx32,rn(rs),rn(rt),bt);break;
    case 6:snprintf(b,n,"blez %s,0x%08"PRIx32,rn(rs),bt);break;case 7:snprintf(b,n,"bgtz %s,0x%08"PRIx32,rn(rs),bt);break;
    case 8:case 9:snprintf(b,n,"addiu %s,%s,%d",rn(rt),rn(rs),si);break;case 10:snprintf(b,n,"slti %s,%s,%d",rn(rt),rn(rs),si);break;
    case 12:snprintf(b,n,"andi %s,%s,0x%x",rn(rt),rn(rs),ui);break;case 13:snprintf(b,n,"ori %s,%s,0x%x",rn(rt),rn(rs),ui);break;
    case 15:snprintf(b,n,"lui %s,0x%x",rn(rt),ui);break;
    case 32:snprintf(b,n,"lb %s,%d(%s)",rn(rt),si,rn(rs));break;case 33:snprintf(b,n,"lh %s,%d(%s)",rn(rt),si,rn(rs));break;
    case 35:snprintf(b,n,"lw %s,%d(%s)",rn(rt),si,rn(rs));break;case 36:snprintf(b,n,"lbu %s,%d(%s)",rn(rt),si,rn(rs));break;
    case 37:snprintf(b,n,"lhu %s,%d(%s)",rn(rt),si,rn(rs));break;case 40:snprintf(b,n,"sb %s,%d(%s)",rn(rt),si,rn(rs));break;
    case 41:snprintf(b,n,"sh %s,%d(%s)",rn(rt),si,rn(rs));break;case 43:snprintf(b,n,"sw %s,%d(%s)",rn(rt),si,rn(rs));break;
    default:snprintf(b,n,"op=0x%x rs=%s rt=%s imm=0x%x",op,rn(rs),rn(rt),ui);break;
  }
}
int main(int argc,char **argv){
  const char *path=argc>1?argv[1]:"REBUILD/files/SCUS_942.88";Exe e=load_exe(path);uint32_t start=argc>2?(uint32_t)strtoul(argv[2],NULL,0):0x80054eacu;uint32_t end=argc>3?(uint32_t)strtoul(argv[3],NULL,0):0x80055280u;
  printf("exe_load=0x%08"PRIx32" bytes=%zu\n",e.load,e.n);
  for(uint32_t pc=start;pc<end;pc+=4){uint32_t w=word(&e,pc);char d[128];decode(pc,w,d,sizeof(d));printf("0x%08"PRIx32"  %08"PRIx32"  %s\n",pc,w,d);}
  printf("-- direct callers --\n");
  size_t payload=le32(e.p+0x1c);for(uint32_t pc=e.load;pc+4<=e.load+payload;pc+=4){uint32_t w=word(&e,pc);if((w>>26)==3){uint32_t t=((pc+4)&0xf0000000)|((w&0x03ffffff)<<2);if(t==start)printf("0x%08"PRIx32"\n",pc);}}
  printf("-- gp-relative memory in function --\n");
  for(uint32_t pc=start;pc<end;pc+=4){uint32_t w=word(&e,pc);unsigned op=w>>26,rs=(w>>21)&31;if(rs==28&&(op==32||op==33||op==35||op==36||op==37||op==40||op==41||op==43))printf("0x%08"PRIx32" op=0x%x imm=%d\n",pc,op,(int16_t)w);}
  free(e.p);return 0;
}
