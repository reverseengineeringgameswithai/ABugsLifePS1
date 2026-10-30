#define _POSIX_C_SOURCE 200809L
#include <ctype.h>
#include <glob.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static int insn(const char*s){while(isspace((unsigned char)*s))s++;if(!*s||*s=='#'||!strncmp(s,".set",4)||!strncmp(s,".text",5))return 0;if(!strncmp(s,".L_",3)&&strchr(s,':'))return 0;return 1;}
static uint32_t base_from(const char*s){const char*p=strstr(s," @ 0x");return p?(uint32_t)strtoul(p+3,NULL,16):0;}
int main(void){glob_t g={0};if(glob("asm/hand_written/*.s",0,NULL,&g))return 2;unsigned hits=0;for(size_t k=0;k<g.gl_pathc;k++){FILE*f=fopen(g.gl_pathv[k],"r");if(!f)return 2;char*line=NULL;size_t cap=0;uint32_t base=0,pc=0;while(getline(&line,&cap,f)>=0){if(!base){base=base_from(line);if(base)pc=base;}char*s=line;while(isspace((unsigned char)*s))s++;size_t n=strlen(s);while(n&&(s[n-1]=='\n'||s[n-1]=='\r'))s[--n]=0;if(base&&insn(s)){if(strstr(s,"25948")||strstr(s,"26019")){printf("%s\t0x%08x\t%s\n",g.gl_pathv[k],pc,s);hits++;}pc+=4;}}free(line);fclose(f);}printf("SUMMARY files=%zu literal_sites=%u\n",g.gl_pathc,hits);globfree(&g);return 0;}
