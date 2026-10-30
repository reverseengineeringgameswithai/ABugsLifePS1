#define _POSIX_C_SOURCE 200809L
#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <inttypes.h>
#include <limits.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#define TARGET_ADDR 0x800a659eu
#define PLAYER_LO   0x800a6500u
#define PLAYER_HI   0x800a65a8u
#define EXE_RAM_BASE 0x8000f800u
#define MAX_OPS 4

typedef struct { char *name; uint32_t pc; } Label;
typedef struct {
    uint32_t pc, target, raw_word;
    char mnemonic[16], ops[MAX_OPS][96], raw[256];
    int op_count, has_target, is_raw;
} Ins;
typedef struct {
    char *path;
    uint32_t base;
    Ins *ins; size_t nins, capins;
    Label *labels; size_t nlabels, caplabels;
    unsigned char *reachable;
} Func;
typedef enum { VK_UNKNOWN, VK_CONST, VK_EXPR } ValKind;
typedef struct { ValKind kind; uint32_t c; char text[128]; } Val;
typedef struct {
    uint32_t pc, address;
    int width, store, absolute;
    char mnemonic[16], value[128], address_expr[128], path[PATH_MAX];
} Access;
typedef struct {
    uint32_t pc, target;
    char args[4][128], path[PATH_MAX];
} Call;

typedef struct {
    Func *funcs; size_t nfuncs, capfuncs;
    Access *accesses; size_t naccesses, capaccesses;
    Call *calls; size_t ncalls, capcalls;
    uint64_t total_instructions;
} Analysis;
typedef struct { uint32_t pc; int store; const char *role; } AccessRole;

static const char *reg_names[32] = {
    "$zero","$at","$v0","$v1","$a0","$a1","$a2","$a3",
    "$t0","$t1","$t2","$t3","$t4","$t5","$t6","$t7",
    "$s0","$s1","$s2","$s3","$s4","$s5","$s6","$s7",
    "$t8","$t9","$k0","$k1","$gp","$sp","$fp","$ra"
};
static const uint32_t focus_addrs[] = {
    0x80038e48u,0x80041a74u,0x80046cacu,0x800524b8u,
    0x80052508u,0x8005bfbcu,0x8005c258u,0x8005c818u,0x8005c918u
};
static const AccessRole latch_roles[] = {
    {0x80047a58u,1,"contact response writes independent state 12"},
    {0x80047e6cu,0,"contact response reads current interaction state"},
    {0x80047e7cu,1,"contact response clears its consumed state"},
    {0x800483acu,1,"player input-history reset branch clears interaction state"},
    {0x800486dcu,0,"player vertical update dispatches state 11"},
    {0x80048700u,1,"grounded player update clears state 11"},
    {0x8004872cu,0,"player vertical update dispatches state 12"},
    {0x80049044u,0,"player action gate excludes interaction states 12 and above"},
    {0x8004a87cu,1,"resident level transition clears interaction state"},
    {0x80051b8cu,0,"gameplay presentation submits the state-11 overhead effect"},
    {0x80051ea4u,1,"harvester activation clears interaction state"},
    {0x80055710u,0,"shared airborne effect/audio helper reads nonzero state"},
    {0x80055ab0u,0,"state-12 release effect requires interaction state zero"},
    {0x800568c0u,0,"skinned player update selects animation for state 11"},
    {0x8005b314u,1,"respawn clears interaction state"},
    {0x8005c3b8u,0,"propeller inner-band test reads state 11"},
    {0x8005c3dcu,0,"propeller release test reads state 12"},
    {0x8005c3f0u,1,"propeller clears state 12 only"},
    {0x8005c8bcu,1,"dandelion writes state 11"}
};

static void die(const char *fmt, ...) {
    va_list ap; va_start(ap,fmt); fprintf(stderr,"phase4_b03_asm_static: ");
    vfprintf(stderr,fmt,ap); fputc('\n',stderr); va_end(ap); exit(1);
}
static void *xrealloc(void *p,size_t n) { void *q=realloc(p,n); if(!q)die("out of memory"); return q; }
static char *xstrdup(const char *s) { char *p=strdup(s); if(!p)die("out of memory"); return p; }
static char *trim(char *s) { while(isspace((unsigned char)*s))s++; char *e=s+strlen(s); while(e>s&&isspace((unsigned char)e[-1]))*--e=0; return s; }
static int ends_with(const char *s,const char *suffix) { size_t a=strlen(s),b=strlen(suffix); return a>=b&&!strcmp(s+a-b,suffix); }
static int parse_i64(const char *s,int64_t *out) { char *e; errno=0; long long v=strtoll(s,&e,0); while(isspace((unsigned char)*e))e++; if(errno||*e)return 0; *out=v; return 1; }
static uint32_t filename_base(const char *path) {
    const char *b=strrchr(path,'/'); b=b?b+1:path; char tmp[9];
    if (strlen(b) < 8) die("filename lacks address: %s", path);
    memcpy(tmp, b, 8);
    tmp[8] = 0;
    char *e; unsigned long v=strtoul(tmp,&e,16); if(*e)die("bad address filename: %s",path); return (uint32_t)v;
}
static int reg_index(const char *s) {
    for(int i=0;i<32;i++)if(!strcmp(s,reg_names[i]))return i;
    if (!strcmp(s, "$0")) return 0;
    return -1;
}
static void val_unknown(Val *v) { v->kind=VK_UNKNOWN; v->c=0; strcpy(v->text,"unknown"); }
static void val_const(Val *v,uint32_t c) { v->kind=VK_CONST; v->c=c; snprintf(v->text,sizeof(v->text),"0x%08x",c); }
static void val_expr(Val *v,const char *fmt,...) { va_list ap; v->kind=VK_EXPR; va_start(ap,fmt); vsnprintf(v->text,sizeof(v->text),fmt,ap); va_end(ap); }
static void init_regs(Val r[32]) { for(int i=0;i<32;i++){ val_expr(&r[i],"%s",reg_names[i]); } val_const(&r[0],0); }
static void json_string(const char *s) { putchar('"'); for(;*s;s++){ unsigned char c=*s; if(c=='"'||c=='\\')printf("\\%c",c); else if(c=='\n')printf("\\n"); else if(c=='\t')printf("\\t"); else if(c<32)printf("\\u%04x",c); else putchar(c); } putchar('"'); }

static void add_ins(Func *f,const Ins *in) { if(f->nins==f->capins){f->capins=f->capins?f->capins*2:128;f->ins=xrealloc(f->ins,f->capins*sizeof(*f->ins));} f->ins[f->nins++]=*in; }
static void add_label(Func *f,const char *name,uint32_t pc) { if(f->nlabels==f->caplabels){f->caplabels=f->caplabels?f->caplabels*2:32;f->labels=xrealloc(f->labels,f->caplabels*sizeof(*f->labels));} f->labels[f->nlabels++]=(Label){xstrdup(name),pc}; }
static void split_ops(char *s,Ins *in) {
    int depth=0; char *start=s;
    for(char *p=s;;p++) { char c=*p; if(c=='(')depth++; else if(c==')')depth--; if((c==','&&depth==0)||c==0) { if(in->op_count<MAX_OPS){ if(c)*p=0; char *t=trim(start); snprintf(in->ops[in->op_count++],96,"%s",t); } if(!c)break; start=p+1; } }
}
static uint32_t branch_target_raw(uint32_t pc,uint32_t w) { int16_t imm=(int16_t)(w&0xffff); return pc+4+((int32_t)imm<<2); }
static void decode_raw(Ins *in,uint32_t w) {
    uint32_t op=w>>26; in->raw_word=w; in->is_raw=1;
    if(op==2||op==3){ strcpy(in->mnemonic,op==2?"j":"jal"); in->target=((in->pc+4)&0xf0000000u)|((w&0x03ffffffu)<<2); in->has_target=1; snprintf(in->ops[0],96,"0x%08x",in->target); in->op_count=1; return; }
    if(op==4||op==5||op==6||op==7||op==1){ strcpy(in->mnemonic,op==4?"beq":op==5?"bne":op==6?"blez":op==7?"bgtz":"regimm"); in->target=branch_target_raw(in->pc,w); in->has_target=1; snprintf(in->ops[0],96,"0x%08x",in->target); in->op_count=1; return; }
    strcpy(in->mnemonic,".word");
}
static uint32_t resolve_label(const Func *f,const char *name,int *ok) { for(size_t i=0;i<f->nlabels;i++)if(!strcmp(f->labels[i].name,name)){*ok=1;return f->labels[i].pc;} *ok=0;return 0; }
static void resolve_targets(Func *f) {
    for(size_t i=0;i<f->nins;i++) { Ins *in=&f->ins[i]; if(in->has_target)continue; const char *t=NULL;
        if(!strcmp(in->mnemonic,"j")||!strcmp(in->mnemonic,"jal")) { if(in->op_count)t=in->ops[0]; }
        else if(!strcmp(in->mnemonic,"beq")||!strcmp(in->mnemonic,"bne")) { if(in->op_count>=3)t=in->ops[2]; }
        else if(!strcmp(in->mnemonic,"blez")||!strcmp(in->mnemonic,"bgtz")||!strcmp(in->mnemonic,"bltz")||!strcmp(in->mnemonic,"bgez")||!strcmp(in->mnemonic,"beqz")||!strcmp(in->mnemonic,"bnez")) { if(in->op_count>=2)t=in->ops[1]; }
        if(t){ int64_t n; if(parse_i64(t,&n)){in->target=(uint32_t)n;in->has_target=1;} else {int ok;uint32_t v=resolve_label(f,t,&ok);if(ok){in->target=v;in->has_target=1;}} }
    }
}
static Func parse_file(const char *path) {
    Func f={0}; f.path=xstrdup(path); f.base=filename_base(path); FILE *fp=fopen(path,"r"); if(!fp)die("open %s: %s",path,strerror(errno));
    char *line=NULL; size_t cap=0; uint32_t pc=f.base;
    while(getline(&line,&cap,fp)>=0){ char original[256]; snprintf(original,sizeof(original),"%s",trim(line)); char *s=trim(line); if(!*s||*s=='#'||!strncmp(s,".set",4)||!strcmp(s,".text"))continue;
        size_t len=strlen(s); if(len&&s[len-1]==':'){s[len-1]=0;add_label(&f,trim(s),pc);continue;}
        char *hash=strchr(s,'#'); if(hash)*hash=0; s=trim(s); if(!*s)continue; Ins in={0};in.pc=pc;snprintf(in.raw,sizeof(in.raw),"%s",original);
        char *ws=s; while(*ws&&!isspace((unsigned char)*ws))ws++; char save=*ws;*ws=0;snprintf(in.mnemonic,sizeof(in.mnemonic),"%s",s);*ws=save;char *rest=trim(ws);
        if(!strcmp(in.mnemonic,".word")){int64_t n;if(!parse_i64(rest,&n))die("bad .word in %s",path);decode_raw(&in,(uint32_t)n);} else if(*rest)split_ops(rest,&in);
        add_ins(&f,&in);pc+=4;
    }
    free(line);fclose(fp);resolve_targets(&f);return f;
}
static int cmp_func(const void *a,const void *b){const Func*x=a,*y=b;if(x->base<y->base)return-1;if(x->base>y->base)return 1;return strcmp(x->path,y->path);}
static void add_func(Analysis *a,Func f){if(a->nfuncs==a->capfuncs){a->capfuncs=a->capfuncs?a->capfuncs*2:64;a->funcs=xrealloc(a->funcs,a->capfuncs*sizeof(*a->funcs));}a->funcs[a->nfuncs++]=f;a->total_instructions+=f.nins;}
static void scan_dir(Analysis *a,const char *dir){DIR*d=opendir(dir);if(!d)die("opendir %s: %s",dir,strerror(errno));struct dirent*e;while((e=readdir(d))){if(e->d_name[0]=='.'||!ends_with(e->d_name,".s"))continue;char p[PATH_MAX];if(snprintf(p,sizeof(p),"%s/%s",dir,e->d_name)>=(int)sizeof(p))die("path too long");add_func(a,parse_file(p));}closedir(d);qsort(a->funcs,a->nfuncs,sizeof(*a->funcs),cmp_func);}
static int ins_index_pc(const Func *f,uint32_t pc){if(pc<f->base||((pc-f->base)&3))return-1;size_t i=(pc-f->base)/4;return i<f->nins&&(f->ins[i].pc==pc)?(int)i:-1;}
static int is_branch(const Ins*in){return !strcmp(in->mnemonic,"beq")||!strcmp(in->mnemonic,"bne")||!strcmp(in->mnemonic,"beqz")||!strcmp(in->mnemonic,"bnez")||!strcmp(in->mnemonic,"blez")||!strcmp(in->mnemonic,"bgtz")||!strcmp(in->mnemonic,"bltz")||!strcmp(in->mnemonic,"bgez")||!strcmp(in->mnemonic,"regimm");}
static void mark_reachable(Func*f){f->reachable=calloc(f->nins,1);unsigned char*queued=calloc(f->nins,1),*blocked=calloc(f->nins,1);size_t*q=malloc((f->nins?f->nins:1)*sizeof(*q)),head=0,tail=0;if(!f->nins)goto out;q[tail++]=0;queued[0]=1;
    while(head<tail){size_t i=q[head++];f->reachable[i]=1;Ins*in=&f->ins[i];
#define ENQ(j) do{size_t _j=(j);if(_j<f->nins&&!queued[_j]){queued[_j]=1;q[tail++]=_j;}}while(0)
        if(is_branch(in)){ENQ(i+1);ENQ(i+2);if(in->has_target){int j=ins_index_pc(f,in->target);if(j>=0)ENQ((size_t)j);}}
        else if(!strcmp(in->mnemonic,"j")){if(i+1<f->nins){blocked[i+1]=1;ENQ(i+1);}if(in->has_target){int j=ins_index_pc(f,in->target);if(j>=0)ENQ((size_t)j);}}
        else if(!strcmp(in->mnemonic,"jal")){ENQ(i+1);ENQ(i+2);}
        else if(!strcmp(in->mnemonic,"jr")){if(i+1<f->nins){blocked[i+1]=1;ENQ(i+1);}}
        else if(!blocked[i])ENQ(i+1);
#undef ENQ
    }
out: free(queued);free(blocked);free(q);}
static int parse_mem(const char*s,int64_t*off,int*base){const char*l=strchr(s,'('),*r=strchr(s,')');if(!l||!r||r<l)return 0;char a[64],b[64];size_t n=(size_t)(l-s);if(n>=sizeof(a)||(size_t)(r-l-1)>=sizeof(b))return 0;memcpy(a,s,n);a[n]=0;memcpy(b,l+1,(size_t)(r-l-1));b[r-l-1]=0;if(!parse_i64(trim(a),off))return 0;*base=reg_index(trim(b));return *base>=0;}
static int width_for(const char*m){if(!strcmp(m,"lb")||!strcmp(m,"lbu")||!strcmp(m,"sb"))return 1;if(!strcmp(m,"lh")||!strcmp(m,"lhu")||!strcmp(m,"sh"))return 2;if(!strcmp(m,"lw")||!strcmp(m,"sw"))return 4;return 0;}
static int is_store_m(const char*m){return !strcmp(m,"sb")||!strcmp(m,"sh")||!strcmp(m,"sw");}
static int is_load_m(const char*m){return !strcmp(m,"lb")||!strcmp(m,"lbu")||!strcmp(m,"lh")||!strcmp(m,"lhu")||!strcmp(m,"lw");}
static void add_access(Analysis*a,const Func*f,const Ins*in,int width,int store,const Val*addr,const Val*value){if(a->naccesses==a->capaccesses){a->capaccesses=a->capaccesses?a->capaccesses*2:256;a->accesses=xrealloc(a->accesses,a->capaccesses*sizeof(*a->accesses));}Access*x=&a->accesses[a->naccesses++];memset(x,0,sizeof(*x));x->pc=in->pc;x->width=width;x->store=store;x->absolute=addr->kind==VK_CONST;x->address=addr->c;snprintf(x->mnemonic,sizeof(x->mnemonic),"%s",in->mnemonic);snprintf(x->value,sizeof(x->value),"%s",value->text);snprintf(x->address_expr,sizeof(x->address_expr),"%s",addr->text);snprintf(x->path,sizeof(x->path),"%s",f->path);}
static void binary_expr(Val*d,const Val*a,const Val*b,const char*op){if(a->kind==VK_CONST&&b->kind==VK_CONST){uint32_t v=!strcmp(op,"+")?a->c+b->c:!strcmp(op,"-")?a->c-b->c:!strcmp(op,"|")?a->c|b->c:a->c&b->c;val_const(d,v);}else{char left[128],right[128];snprintf(left,sizeof(left),"%s",a->text);snprintf(right,sizeof(right),"%s",b->text);val_expr(d,"(%s%s%s)",left,op,right);}}
static void exec_noncontrol(Analysis*a,const Func*f,const Ins*in,Val r[32],int record){int d=in->op_count?reg_index(in->ops[0]):-1,s=in->op_count>1?reg_index(in->ops[1]):-1,t=in->op_count>2?reg_index(in->ops[2]):-1;int64_t imm;
    if(!strcmp(in->mnemonic,"lui")&&d>=0&&in->op_count>1&&parse_i64(in->ops[1],&imm))val_const(&r[d],(uint32_t)imm<<16);
    else if((!strcmp(in->mnemonic,"addiu")||!strcmp(in->mnemonic,"addi"))&&d>=0&&s>=0&&in->op_count>2&&parse_i64(in->ops[2],&imm)){Val v;val_const(&v,(uint32_t)(int32_t)imm);binary_expr(&r[d],&r[s],&v,"+");}
    else if(!strcmp(in->mnemonic,"ori")&&d>=0&&s>=0&&in->op_count>2&&parse_i64(in->ops[2],&imm)){Val v;val_const(&v,(uint32_t)imm);binary_expr(&r[d],&r[s],&v,"|");}
    else if(!strcmp(in->mnemonic,"andi")&&d>=0&&s>=0&&in->op_count>2&&parse_i64(in->ops[2],&imm)){Val v;val_const(&v,(uint32_t)imm);binary_expr(&r[d],&r[s],&v,"&");}
    else if((!strcmp(in->mnemonic,"addu")||!strcmp(in->mnemonic,"subu")||!strcmp(in->mnemonic,"or"))&&d>=0&&s>=0&&t>=0){binary_expr(&r[d],&r[s],&r[t],!strcmp(in->mnemonic,"subu")?"-":!strcmp(in->mnemonic,"or")?"|":"+");}
    else if(!strcmp(in->mnemonic,"sll")&&d>=0&&s>=0&&in->op_count>2&&parse_i64(in->ops[2],&imm)){if(r[s].kind==VK_CONST)val_const(&r[d],r[s].c<<(imm&31));else{char src[128];snprintf(src,sizeof(src),"%s",r[s].text);val_expr(&r[d],"(%s<<%lld)",src,(long long)imm);}}
    else if((is_load_m(in->mnemonic)||is_store_m(in->mnemonic))&&in->op_count>=2){int64_t off;int b;if(parse_mem(in->ops[1],&off,&b)){Val av;if(r[b].kind==VK_CONST)val_const(&av,r[b].c+(uint32_t)(int32_t)off);else val_expr(&av,"%s%+lld",r[b].text,(long long)off);int width=width_for(in->mnemonic),store=is_store_m(in->mnemonic);Val vv;if(store&&d>=0)vv=r[d];else val_expr(&vv,"loaded-result");if(record)add_access(a,f,in,width,store,&av,&vv);if(is_load_m(in->mnemonic)&&d>=0)val_expr(&r[d],"mem%d(%s)",width*8,av.text);}}
    else if(!strcmp(in->mnemonic,"move")&&d>=0&&s>=0)r[d]=r[s];
    else if(d>0&&!is_branch(in)&&strcmp(in->mnemonic,"j")&&strcmp(in->mnemonic,"jal")&&strcmp(in->mnemonic,"jr")&&strcmp(in->mnemonic,"nop")&&strcmp(in->mnemonic,"mult")&&strcmp(in->mnemonic,"multu")&&strcmp(in->mnemonic,".word"))val_unknown(&r[d]);
    val_const(&r[0],0);
}
static void add_call(Analysis*a,const Func*f,const Ins*in,const Val r[32],const Ins*delay){if(a->ncalls==a->capcalls){a->capcalls=a->capcalls?a->capcalls*2:64;a->calls=xrealloc(a->calls,a->capcalls*sizeof(*a->calls));}Val tmp[32];memcpy(tmp,r,sizeof(tmp));if(delay)exec_noncontrol(a,f,delay,tmp,0);Call*c=&a->calls[a->ncalls++];memset(c,0,sizeof(*c));c->pc=in->pc;c->target=in->target;for(int i=0;i<4;i++)snprintf(c->args[i],sizeof(c->args[i]),"%s",tmp[4+i].text);snprintf(c->path,sizeof(c->path),"%s",f->path);}
static void analyze_func(Analysis*a,Func*f){mark_reachable(f);Val r[32];init_regs(r);for(size_t i=0;i<f->nins;i++){Ins*in=&f->ins[i];if(!strcmp(in->mnemonic,"jal")&&in->has_target)add_call(a,f,in,r,i+1<f->nins?&f->ins[i+1]:NULL);exec_noncontrol(a,f,in,r,1);}}
static Func*find_func(Analysis*a,uint32_t base){for(size_t i=0;i<a->nfuncs;i++)if(a->funcs[i].base==base)return&a->funcs[i];return NULL;}
static int access_match(const Analysis*a,uint32_t pc,uint32_t addr,int store,const char*value){for(size_t i=0;i<a->naccesses;i++){const Access*x=&a->accesses[i];if(x->pc==pc&&x->absolute&&x->address==addr&&x->store==store&&(!value||!strcmp(x->value,value)))return 1;}return 0;}
static int is_player_relative_latch_pc(uint32_t pc){return pc==0x800486dcu||pc==0x80048700u||pc==0x8004872cu||pc==0x80049044u;}
static const Access*role_access(const Analysis*a,const AccessRole*r){for(size_t i=0;i<a->naccesses;i++){const Access*x=&a->accesses[i];if(x->pc!=r->pc||x->store!=r->store)continue;if(x->absolute&&x->address==TARGET_ADDR)return x;if(is_player_relative_latch_pc(r->pc)&&!x->absolute&&strstr(x->path,"80048138")&&strstr(x->address_expr,"+158"))return x;}return NULL;}
static int call_match(const Analysis*a,uint32_t pc,uint32_t target){for(size_t i=0;i<a->ncalls;i++)if(a->calls[i].pc==pc&&a->calls[i].target==target)return 1;return 0;}
static int call_arg_match(const Analysis*a,uint32_t pc,uint32_t target,int arg,const char*value){for(size_t i=0;i<a->ncalls;i++)if(a->calls[i].pc==pc&&a->calls[i].target==target&&arg>=0&&arg<4&&!strcmp(a->calls[i].args[arg],value))return 1;return 0;}
static int ins_has(Analysis*a,uint32_t base,uint32_t pc,const char*mnemonic,const char*fragment){Func*f=find_func(a,base);if(!f)return 0;int i=ins_index_pc(f,pc);if(i<0)return 0;Ins*in=&f->ins[i];return !strcmp(in->mnemonic,mnemonic)&&(!fragment||strstr(in->raw,fragment));}
static int exe_read(const char*path,uint32_t address,unsigned char*out,size_t size){if(!path||address<EXE_RAM_BASE)return 0;FILE*fp=fopen(path,"rb");if(!fp)return 0;long off=(long)(address-EXE_RAM_BASE);int ok=fseek(fp,off,SEEK_SET)==0&&fread(out,1,size,fp)==size;fclose(fp);return ok;}
static int exe_u16(const char*path,uint32_t address,uint16_t*out){unsigned char b[2];if(!exe_read(path,address,b,sizeof(b)))return 0;*out=(uint16_t)(b[0]|((uint16_t)b[1]<<8));return 1;}
static int exe_u32(const char*path,uint32_t address,uint32_t*out){unsigned char b[4];if(!exe_read(path,address,b,sizeof(b)))return 0;*out=(uint32_t)b[0]|((uint32_t)b[1]<<8)|((uint32_t)b[2]<<16)|((uint32_t)b[3]<<24);return 1;}
static void print_access(const Access*x){printf("{\"pc\":\"0x%08x\",\"kind\":\"%s\",\"width\":%d,\"address\":",x->pc,x->store?"store":"load",x->width);if(x->absolute)printf("\"0x%08x\"",x->address);else json_string(x->address_expr);printf(",\"value\":");json_string(x->value);printf(",\"file\":");json_string(x->path);putchar('}');}
static void print_call(const Call*c){printf("{\"pc\":\"0x%08x\",\"target\":\"0x%08x\",\"a0\":",c->pc,c->target);json_string(c->args[0]);printf(",\"a1\":");json_string(c->args[1]);printf(",\"a2\":");json_string(c->args[2]);printf(",\"a3\":");json_string(c->args[3]);putchar('}');}
static void print_focus(Analysis*a,Func*f){size_t reach=0;for(size_t i=0;i<f->nins;i++)reach+=!!f->reachable[i];printf("{\"address\":\"0x%08x\",\"file\":",f->base);json_string(f->path);printf(",\"instructions\":%zu,\"reachable_from_entry\":%zu,\"unreachable_ranges\":[",f->nins,reach);int first=1;for(size_t i=0;i<f->nins;){if(f->reachable[i]){i++;continue;}size_t j=i;while(j+1<f->nins&&!f->reachable[j+1])j++;if(!first)putchar(',');printf("{\"start\":\"0x%08x\",\"end\":\"0x%08x\"}",f->ins[i].pc,f->ins[j].pc);first=0;i=j+1;}printf("],\"calls\":[");first=1;for(size_t i=0;i<a->ncalls;i++)if(!strcmp(a->calls[i].path,f->path)){if(!first)putchar(',');print_call(&a->calls[i]);first=0;}printf("],\"player_block_accesses\":[");first=1;for(size_t i=0;i<a->naccesses;i++){Access*x=&a->accesses[i];if(strcmp(x->path,f->path)||!x->absolute||x->address<PLAYER_LO||x->address>PLAYER_HI)continue;if(!first)putchar(',');print_access(x);first=0;}printf("]}");}
int main(int argc,char**argv){if(argc<2||argc>3){fprintf(stderr,"usage: %s ASM_HAND_WRITTEN_DIRECTORY [PRISTINE_EXE]\n",argv[0]);return 2;}const char*exe_path=argc==3?argv[2]:NULL;Analysis a={0};scan_dir(&a,argv[1]);for(size_t i=0;i<a.nfuncs;i++)analyze_func(&a,&a.funcs[i]);
    size_t latch_total=0,latch_reads=0,latch_writes=0;int literal_only=1,roles_ok=1;
    for(size_t i=0;i<a.naccesses;i++){Access*x=&a.accesses[i];if(!x->absolute||x->address!=TARGET_ADDR)continue;latch_total++;if(x->store){latch_writes++;if(strcmp(x->value,"0x00000000")&&strcmp(x->value,"0x0000000b")&&strcmp(x->value,"0x0000000c"))literal_only=0;}else latch_reads++;}
    for(size_t i=0;i<sizeof(latch_roles)/sizeof(latch_roles[0]);i++){const Access*x=role_access(&a,&latch_roles[i]);roles_ok&=x!=NULL;if(x&&!x->absolute){latch_total++;if(x->store){latch_writes++;if(strcmp(x->value,"0x00000000")&&strcmp(x->value,"0x0000000b")&&strcmp(x->value,"0x0000000c"))literal_only=0;}else latch_reads++;}}
    int activation_ok=ins_has(&a,0x8005c818u,0x8005c818u,"bne","$s4,$s5")&&ins_has(&a,0x8005c818u,0x8005c828u,"andi","0x2")&&call_arg_match(&a,0x8005c890u,0x80052508u,2,"0x00000028")&&access_match(&a,0x8005c8a4u,0x800a6590u,0,NULL)&&call_arg_match(&a,0x8005c874u,0x8005044cu,0,"0x0000000f");
    int presentation_ok=access_match(&a,0x80051b8cu,TARGET_ADDR,0,NULL)&&access_match(&a,0x80051ba4u,0x800a657cu,0,NULL)&&call_match(&a,0x80051c30u,0x80022fe0u)&&access_match(&a,0x800568c0u,TARGET_ADDR,0,NULL)&&access_match(&a,0x800568d4u,0x800a6588u,1,"0x00000012");
    int lifecycle_ok=role_access(&a,&latch_roles[5])&&access_match(&a,0x8004a87cu,TARGET_ADDR,1,"0x00000000")&&access_match(&a,0x80051ea4u,TARGET_ADDR,1,"0x00000000")&&access_match(&a,0x8005b314u,TARGET_ADDR,1,"0x00000000");
    uint16_t brown_tier3_type=0,brown_tier3_extra=0;uint32_t type8_handler=0;int exe_ok=exe_u16(exe_path,0x8007a450u,&brown_tier3_type)&&exe_u16(exe_path,0x8007a452u,&brown_tier3_extra)&&exe_u32(exe_path,0x8001b860u,&type8_handler);
    int resident_ok=!exe_path||(exe_ok&&brown_tier3_type==8&&brown_tier3_extra==0&&type8_handler==0x8005c818u);
    int gate_pass=latch_total==19&&latch_reads==10&&latch_writes==9&&literal_only&&roles_ok&&activation_ok&&presentation_ok&&lifecycle_ok&&resident_ok;
    printf("{\n \"schema\":\"abl-phase4-b03-asm-static-v2\",\n \"engine\":{\"language\":\"C11\",\"analysis\":[\"textual MIPS parse\",\"raw J/JAL/branch decode\",\"delay-slot call arguments\",\"constant/address propagation\",\"entry CFG reachability\",\"direct latch lifecycle classification\",\"pristine EXE table verification\"]},\n");
    printf(" \"corpus\":{\"directory\":");json_string(argv[1]);printf(",\"files\":%zu,\"instructions\":%"PRIu64"},\n",a.nfuncs,a.total_instructions);
    printf(" \"target_800a659e_accesses\":[");int first=1;for(size_t i=0;i<a.naccesses;i++){Access*x=&a.accesses[i];if(!x->absolute||x->address!=TARGET_ADDR)continue;if(!first)putchar(',');print_access(x);first=0;}printf("],\n \"focus_functions\":[");first=1;for(size_t i=0;i<sizeof(focus_addrs)/sizeof(focus_addrs[0]);i++){Func*f=find_func(&a,focus_addrs[i]);if(!f)continue;if(!first)putchar(',');print_focus(&a,f);first=0;}printf("],\n");
    printf(" \"plant_slot_accesses\":[");first=1;for(size_t i=0;i<a.naccesses;i++){Access*x=&a.accesses[i];if(x->absolute||!strstr(x->address_expr,"$s2")||(!strstr(x->path,"8005c258")&&!strstr(x->path,"8005c818")))continue;if(!first)putchar(',');print_access(x);first=0;}printf("],\n");
    printf(" \"latch_frontier\":{\"scope\":\"direct absolute accesses plus typed player-relative $s1+0x9e accesses in retained hand-written ASM; other indirect and overlay aliases excluded\",\"absolute_sites\":15,\"typed_player_relative_sites\":4,\"total\":%zu,\"reads\":%zu,\"writes\":%zu,\"all_writes_literal_0_11_or_12\":%s,\"all_expected_sites_present\":%s,\"classified_sites\":[",latch_total,latch_reads,latch_writes,literal_only?"true":"false",roles_ok?"true":"false");
    for(size_t i=0;i<sizeof(latch_roles)/sizeof(latch_roles[0]);i++){const Access*x=role_access(&a,&latch_roles[i]);if(i)putchar(',');printf("{\"pc\":\"0x%08x\",\"access\":\"%s\",\"address_form\":\"%s\",\"role\":",latch_roles[i].pc,latch_roles[i].store?"write":"read",x&&x->absolute?"absolute":"typed_player_relative");json_string(latch_roles[i].role);printf(",\"present\":%s}",x?"true":"false");}printf("]},\n");
    printf(" \"activation_contract\":{\"selected_slot_gate\":%s,\"slot_extra_bit_0x02_gate\":%s,\"quantized_xyz_radius\":40,\"sphere_center_y_offset\":-29696,\"harvester_flag_0x80_suppresses_latch\":%s,\"launch_sound_id\":15,\"guard_pass\":%s},\n",ins_has(&a,0x8005c818u,0x8005c818u,"bne","$s4,$s5")?"true":"false",ins_has(&a,0x8005c818u,0x8005c828u,"andi","0x2")?"true":"false",access_match(&a,0x8005c8a4u,0x800a6590u,0,NULL)?"true":"false",activation_ok?"true":"false");
    printf(" \"presentation_contract\":{\"latch11_effect_gate\":\"0x80051b8c\",\"action_lockout_zero_gate\":\"0x80051ba4\",\"effect_submit_call\":\"0x80051c30 -> 0x80022fe0\",\"effect_origin_y_offset\":-22528,\"latch11_animation_writer\":\"0x800568d4\",\"animation\":18,\"guard_pass\":%s,\"exact_display_tail\":\"not attributed; deferred as low return\"},\n",presentation_ok?"true":"false");
    printf(" \"lifecycle_contract\":{\"grounded_clear\":\"0x80048700\",\"level_transition_clear\":\"0x8004a87c\",\"harvester_activation_clear\":\"0x80051ea4\",\"respawn_clear\":\"0x8005b314\",\"no_direct_timer_or_arithmetic_writer\":%s,\"guard_pass\":%s},\n",literal_only?"true":"false",lifecycle_ok?"true":"false");
    printf(" \"resident_binding\":{\"exe_path\":");if(exe_path)json_string(exe_path);else printf("null");printf(",\"table_reads_ok\":%s,\"brown_tier3_type\":%u,\"brown_tier3_extra\":%u,\"type8_handler\":\"0x%08x\",\"guard_pass\":%s},\n",exe_ok?"true":"false",brown_tier3_type,brown_tier3_extra,type8_handler,resident_ok?"true":"false");
    printf(" \"bounded_exhaustion\":{\"high_yield_static_scope\":\"exhausted\",\"phase4_row_solved\":false,\"deferred\":[\"repository-wide indirect player-pointer and overlay alias proof\",\"exhaustive per-stage placement and reachability sampling\",\"exact GPU/display ownership of the short post-clear tail\",\"native dandelion-to-propeller combination replay\"],\"gate_pass\":%s},\n",gate_pass?"true":"false");
    printf(" \"derived_checks\":{");
    printf("\"dandelion_vy_minus4096\":%s,",access_match(&a,0x8005c848u,0x800a6530u,1,"0xfffff000")?"true":"false");
    printf("\"dandelion_mode5\":%s,",access_match(&a,0x8005c854u,0x800a6580u,1,"0x00000005")?"true":"false");
    printf("\"dandelion_latch11\":%s,",access_match(&a,0x8005c8bcu,TARGET_ADDR,1,"0x0000000b")?"true":"false");
    printf("\"release_clears_binding\":%s,",access_match(&a,0x80046d04u,0x800a655cu,1,"0x00000000")?"true":"false");
    printf("\"release_clears_timer\":%s,",access_match(&a,0x80046d00u,0x800a657au,1,"0x00000000")?"true":"false");
    Func*h=find_func(&a,0x8005c818u);int suffix=0;if(h){int j=ins_index_pc(h,0x8005c8d4u);suffix=j>=0&&!h->reachable[j];}
    printf("\"dandelion_shared_suffix_unreachable_from_entry\":%s",suffix?"true":"false");
    printf(",\"bounded_exhaustion_gate\":%s",gate_pass?"true":"false");
    printf("}\n}\n");
    return gate_pass?0:1;
}
