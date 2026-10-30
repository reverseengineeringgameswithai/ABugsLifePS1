#define _POSIX_C_SOURCE 200809L
#include <ctype.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct{const char*path;uint32_t base;}Unit;
static int instruction(const char*s){while(isspace((unsigned char)*s))s++;if(!*s||*s=='#')return 0;if(!strncmp(s,".set",4)||!strncmp(s,".text",5))return 0;if(!strncmp(s,".L_",3)&&strchr(s,':'))return 0;return 1;}
static int relevant(const char*s){const char*keys[]={"25948","26019","92($s2)","163($s2)","92($s1)","0x8000","0x4000","0x270ff","1024","0x40","0xffbf",NULL};for(int i=0;keys[i];i++)if(strstr(s,keys[i]))return 1;return 0;}
int main(void){Unit u[]={{"asm/hand_written/80047284_player_contact_response.s",0x80047284},{"asm/hand_written/80046cac_sub_80046cac.s",0x80046cac}};for(unsigned k=0;k<sizeof u/sizeof u[0];k++){FILE*f=fopen(u[k].path,"r");if(!f){perror(u[k].path);return 1;}printf("UNIT %s base=0x%08x\n",u[k].path,u[k].base);char*line=NULL;size_t cap=0;uint32_t pc=u[k].base;while(getline(&line,&cap,f)>=0){char*s=line;while(isspace((unsigned char)*s))s++;size_t n=strlen(s);while(n&&(s[n-1]=='\n'||s[n-1]=='\r'))s[--n]=0;if(instruction(s)){if(relevant(s))printf("0x%08x\t%s\n",pc,s);pc+=4;}}free(line);fclose(f);printf("END 0x%08x bytes=%u\n",pc,pc-u[k].base);}return 0;}
