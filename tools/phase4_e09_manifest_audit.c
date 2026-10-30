#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static char *read_all(const char *path,size_t*n){FILE*f=fopen(path,"rb");if(!f){perror(path);exit(2);}fseek(f,0,SEEK_END);long z=ftell(f);rewind(f);char*p=malloc((size_t)z+1);if(!p)exit(2);if(fread(p,1,(size_t)z,f)!=(size_t)z)exit(2);fclose(f);p[z]=0;*n=(size_t)z;return p;}
static size_t string_end(const char*s,size_t n,size_t p){for(p++;p<n;p++){if(s[p]=='\\')p++;else if(s[p]=='\"')return p;}return n;}
static size_t object_end(const char*s,size_t n,size_t start){unsigned depth=0;for(size_t p=start;p<n;p++){if(s[p]=='\"'){p=string_end(s,n,p);continue;}if(s[p]=='{')depth++;else if(s[p]=='}'&&!--depth)return p+1;}return n;}
int main(int argc,char**argv){
 if(argc!=2){fprintf(stderr,"usage: %s phase4_trace_capsule_set.json\n",argv[0]);return 2;}size_t n;char*s=read_all(argv[1],&n);size_t stack[256];unsigned sp=0,found=0;
 for(size_t p=0;p<n;p++){
  if(s[p]=='{'){if(sp==256)return 2;stack[sp++]=p;continue;}if(s[p]=='}'){if(sp)sp--;continue;}
  if(s[p]!='\"')continue;size_t e=string_end(s,n,p);if(e==n)break;
  if(sp&&e-p>35){size_t len=e-p-1;char*tmp=malloc(len+1);if(!tmp)return 2;memcpy(tmp,s+p+1,len);tmp[len]=0;
   if(strstr(tmp,"/trace-capsules/Phase4/v2/E09__")){size_t st=stack[sp-1],end=object_end(s,n,st);printf("E09_OBJECT %u\n%.*s\n",++found,(int)(end-st),s+st);}
   free(tmp);
  }p=e;
 }
 fprintf(stderr,"E09 objects: %u\n",found);free(s);return found==12?0:3;
}
