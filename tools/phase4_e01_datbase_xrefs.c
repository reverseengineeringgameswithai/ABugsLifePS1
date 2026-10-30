#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
static uint32_t u32(const unsigned char*p){return(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static const char*opname(unsigned op){switch(op){case 0x20:return"lb";case 0x21:return"lh";case 0x23:return"lw";case 0x24:return"lbu";case 0x25:return"lhu";case 0x28:return"sb";case 0x29:return"sh";case 0x2b:return"sw";case 0x09:return"addiu";case 0x0d:return"ori";default:return"?";}}
int main(void){
 const char*path="REBUILD/files/SCUS_942.88";FILE*f=fopen(path,"rb");if(!f)return 1;fseek(f,0,SEEK_END);long z=ftell(f);rewind(f);unsigned char*d=malloc((size_t)z);if(!d)return 1;if(fread(d,1,(size_t)z,f)!=(size_t)z)return 1;fclose(f);
 if(z<0x800||u32(d)!=0x582d5350u){fprintf(stderr,"bad PS-X EXE\n");return 2;}uint32_t base=u32(d+0x18),sz=u32(d+0x1c);if((uint64_t)0x800+sz>(uint64_t)z)sz=(uint32_t)z-0x800;
 printf("exe=%s load=%08"PRIx32" size=%08"PRIx32"\n",path,base,sz);
 for(uint32_t i=0;i+4<=sz;i+=4){uint32_t w=u32(d+0x800+i),pc=base+i;unsigned op=w>>26,rs=(w>>21)&31,rt=(w>>16)&31;uint16_t im=w;
   if(rs==28&&im==0x6d00u&&(op==0x20||op==0x21||op==0x23||op==0x24||op==0x25||op==0x28||op==0x29||op==0x2b))
     printf("gp-direct pc=%08"PRIx32" insn=%08"PRIx32" %s r%u,0x6d00(gp)\n",pc,w,opname(op),rt);
   if(op==0x0f&&im==0x8008u){unsigned r=rt;for(unsigned k=1;k<=12&&i+4*k+4<=sz;k++){uint32_t x=u32(d+0x800+i+4*k);unsigned xo=x>>26,xrs=(x>>21)&31,xrt=(x>>16)&31;uint16_t xim=x;
       if(xrs==r&&xim==0x2498u&&(xo==0x20||xo==0x21||xo==0x23||xo==0x24||xo==0x25||xo==0x28||xo==0x29||xo==0x2b))
         printf("absolute pc=%08"PRIx32" via_lui=%08"PRIx32" insn=%08"PRIx32" %s r%u,0x2498(r%u) gap=%u\n",base+i+4*k,pc,x,opname(xo),xrt,r,k);
       if(xrt==r&&k>1&&(xo==0x00||xo==0x09||xo==0x0d||xo==0x0f||xo==0x23))break;
   }}
 }free(d);return 0;
}
