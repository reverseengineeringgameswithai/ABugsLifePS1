#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

static char *load(const char *p, size_t *n) {
  FILE *f=fopen(p,"rb"); if(!f){perror(p); exit(2);} fseek(f,0,SEEK_END); long z=ftell(f); rewind(f);
  char *b=malloc((size_t)z+1); if(!b) exit(2); if(fread(b,1,(size_t)z,f)!=(size_t)z) exit(2); fclose(f); b[z]=0; *n=(size_t)z; return b;
}
static long long field(const char *a,const char *z,const char *name,int *ok){
  char pat[96]; snprintf(pat,sizeof pat,"\"name\": \"%s\"",name); const char *p=strstr(a,pat); if(!p||p>=z){*ok=0;return 0;}
  p=strstr(p,"\"value\":"); if(!p||p>=z){*ok=0;return 0;} p+=8; *ok=1; return strtoll(p,NULL,10);
}
int main(int argc,char **argv){
  const char *record_mark="\n    {\n      \"address\": \"0x";
  if(argc!=2){fprintf(stderr,"usage: %s inventory.json\n",argv[0]);return 2;} size_t n; char *b=load(argv[1],&n),*p=b; int total=0, mosq=0;
  while((p=strstr(p,record_mark))){
    p += strlen(record_mark) - strlen("\"address\": \"0x");
    char *fields=strstr(p,"\"fields\": ["); if(!fields)break; char *next=strstr(fields,"\n    {\n      \"address\":"); char *z=next?next:b+n;
    unsigned addr=0; sscanf(p,"\"address\": \"0x%x",&addr); int ok=0; long long id=field(fields,z,"id",&ok); if(!ok){p=fields+10;continue;} total++;
    int k; long long cb=field(fields,z,"callback",&k); if(id==10 && k && (uint32_t)cb==0x8004a180u){
      long long x=field(fields,z,"x",&k), y=field(fields,z,"y",&k), zz=field(fields,z,"z",&k);
      long long vx=field(fields,z,"vx",&k), vy=field(fields,z,"vy",&k), vz=field(fields,z,"vz",&k);
      long long st=field(fields,z,"state44",&k), fl=field(fields,z,"flags",&k), tm=field(fields,z,"timer6c",&k);
      long long pr=field(fields,z,"program",&k), dat=field(fields,z,"data",&k);
      printf("mosquito[%d] actor=0x%08x pos=(%lld,%lld,%lld) vel=(%lld,%lld,%lld) state44=%lld flags=0x%08x timer6c=%lld program=0x%08x data=0x%08x callback=0x%08x\n",mosq,addr,x,y,zz,vx,vy,vz,st,(unsigned)fl,tm,(unsigned)pr,(unsigned)dat,(unsigned)cb); mosq++;
    }
    p=fields+10;
  }
  printf("summary actor_records=%d mosquito_records=%d identity_rule=(id==10 && callback==0x8004a180)\n",total,mosq); free(b); return mosq?0:1;
}
