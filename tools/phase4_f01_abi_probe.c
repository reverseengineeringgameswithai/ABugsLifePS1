/*
 * phase4_f01_abi_probe.c -- compiled instruction probe for the F01 ABI ledger.
 *
 * Python supplies a hash-checked manifest of images and STATIC-INDEX extents.
 * This program alone reads and decodes the MIPS words.  Its proofs deliberately
 * fail closed at context-sensitive delay-slot entries and unsupported words.
 */

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_IMAGES 32
#define MAX_FUNCS 1024
#define MAX_WORDS 4096
#define MAX_STACK_SLOTS 128
#define MAX_HOISTS 64
#define MAX_RA_HAZARDS 64

static const char *REGS[32] = {
    "zero", "at", "v0", "v1", "a0", "a1", "a2", "a3",
    "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7",
    "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
    "t8", "t9", "k0", "k1", "gp", "sp", "fp", "ra"
};
static const int CALLEE_REGS[10] = {16,17,18,19,20,21,22,23,30,31};
static const int CALLER_REGS[17] = {1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,24,25};

typedef struct {
    char id[64], path[512];
    uint32_t base, gp;
    size_t declared_size, size;
    uint8_t *bytes;
} Image;

typedef struct {
    int image;
    uint32_t entry, end;
    uint32_t entry_call_witness_pc;
    int entry_sp_call_proved;
    char name[160];
} Func;

typedef struct { int image; uint32_t load_pc, logged_pc; } Hoist;
typedef struct { int image; uint32_t site_pc, observed_target; } RaHazard;

static Image IMAGES[MAX_IMAGES]; static int NIMAGES;
static Func FUNCS[MAX_FUNCS]; static int NFUNCS;
static Hoist HOISTS[MAX_HOISTS]; static int NHOISTS;
static RaHazard RA_HAZARDS[MAX_RA_HAZARDS]; static int NRA_HAZARDS;

enum { ROLE_MEMORY_BASE=1u, ROLE_STORE_VALUE=2u, ROLE_ARITHMETIC=4u,
       ROLE_BRANCH=8u, ROLE_INDIRECT_TARGET=16u, ROLE_MERGE_VALUE=32u };

typedef struct {
    uint32_t reads, writes;
    uint32_t roles[32];
    int known, is_load, is_store, width;
    int base, value;
    int32_t imm;
} Decoded;

enum { SP_BOTTOM=0, SP_EXACT=1, SP_UNKNOWN=2 };
typedef struct { uint8_t kind; int32_t delta; } SpState;
enum { R_ENTRY=0, R_MODIFIED=1, R_UNKNOWN=2, R_BOTTOM=3 };

static void die(const char *what, const char *detail)
{
    fprintf(stderr, "phase4 f01 abi probe: %s%s%s\n", what,
            detail ? ": " : "", detail ? detail : "");
    exit(2);
}

static uint32_t le32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static uint8_t *slurp(const char *path, size_t *size)
{
    FILE *f = fopen(path, "rb"); long n; uint8_t *p;
    if (!f) die("cannot open image", path);
    if (fseek(f, 0, SEEK_END) || (n = ftell(f)) < 0 || fseek(f, 0, SEEK_SET))
        die("cannot size image", path);
    p = malloc(n ? (size_t)n : 1u); if (!p) die("out of memory", NULL);
    if (n && fread(p, 1, (size_t)n, f) != (size_t)n) die("cannot read image", path);
    if (fclose(f)) die("cannot close image", path);
    *size = (size_t)n; return p;
}

static int image_index(const char *id)
{
    int i; for (i=0;i<NIMAGES;i++) if (!strcmp(IMAGES[i].id,id)) return i;
    return -1;
}

static uint32_t word_at(const Image *im,uint32_t pc);
static int is_call(uint32_t w);
static uint32_t direct_target(uint32_t w,uint32_t pc);

static void read_manifest(const char *path)
{
    FILE *f=fopen(path,"r"); char line[1600];
    if (!f) die("cannot open manifest",path);
    while (fgets(line,sizeof line,f)) {
        char kind[32]; if (line[0]=='#'||line[0]=='\n') continue;
        if (sscanf(line,"%31s",kind)!=1) continue;
        if (!strcmp(kind,"VERSION")) {
            int v=0; if (sscanf(line,"VERSION %d",&v)!=1||v!=1) die("bad manifest version",line);
        } else if (!strcmp(kind,"IMAGE")) {
            unsigned base,gp; size_t size; Image *x;
            if (NIMAGES==MAX_IMAGES) die("too many images",NULL);
            x=&IMAGES[NIMAGES];
            if (sscanf(line,"IMAGE %63s %511s %x %zu %x",x->id,x->path,&base,&size,&gp)!=5)
                die("bad IMAGE line",line);
            x->base=base; x->declared_size=size; x->gp=gp; NIMAGES++;
        } else if (!strcmp(kind,"FUNC")) {
            char image[64]; unsigned lo,hi,call_pc; int call_proved; Func *x;
            if (NFUNCS==MAX_FUNCS) die("too many functions",NULL);
            x=&FUNCS[NFUNCS];
            if (sscanf(line,"FUNC %63s %x %x %159s %d %x",image,&lo,&hi,x->name,&call_proved,&call_pc)!=6)
                die("bad FUNC line",line);
            x->image=image_index(image); x->entry=lo; x->end=hi;
            x->entry_sp_call_proved=call_proved; x->entry_call_witness_pc=call_pc;
            if (x->image<0||hi<=lo||((hi-lo)&3u)||
                (call_proved!=0&&call_proved!=1)||(!call_proved&&call_pc))
                die("invalid FUNC line",line);
            NFUNCS++;
        } else if (!strcmp(kind,"HOIST")) {
            char image[64]; unsigned pc,logged; Hoist *x;
            if (NHOISTS==MAX_HOISTS) die("too many hoists",NULL);
            x=&HOISTS[NHOISTS];
            if (sscanf(line,"HOIST %63s %x %x",image,&pc,&logged)!=3) die("bad HOIST line",line);
            x->image=image_index(image); x->load_pc=pc; x->logged_pc=logged;
            if (x->image<0) die("HOIST unknown image",line);
            NHOISTS++;
        } else if (!strcmp(kind,"RAHAZARD")) {
            char image[64]; unsigned site,target; RaHazard *x;
            if (NRA_HAZARDS==MAX_RA_HAZARDS) die("too many RA hazards",NULL);
            x=&RA_HAZARDS[NRA_HAZARDS];
            if (sscanf(line,"RAHAZARD %63s %x %x",image,&site,&target)!=3)
                die("bad RAHAZARD line",line);
            x->image=image_index(image); x->site_pc=site; x->observed_target=target;
            if (x->image<0||target<8) die("invalid RAHAZARD line",line);
            NRA_HAZARDS++;
        } else die("unknown manifest record",kind);
    }
    if (ferror(f)||fclose(f)) die("cannot read manifest",path);
    if (!NIMAGES||!NFUNCS) die("empty manifest",path);
    for (int i=0;i<NIMAGES;i++) {
        IMAGES[i].bytes=slurp(IMAGES[i].path,&IMAGES[i].size);
        if (IMAGES[i].size!=IMAGES[i].declared_size) die("image size differs from manifest",IMAGES[i].id);
    }
    for (int i=0;i<NFUNCS;i++) if (FUNCS[i].entry_sp_call_proved) {
        uint32_t pc=FUNCS[i].entry_call_witness_pc;
        uint32_t w=word_at(&IMAGES[FUNCS[i].image],pc);
        if (!is_call(w)||direct_target(w,pc)!=FUNCS[i].entry)
            die("FUNC entry-call witness is not an exact call edge",FUNCS[i].name);
    }
}

static uint32_t word_at(const Image *im,uint32_t pc)
{
    uint64_t off;
    if (pc<im->base) die("pc below image",im->id);
    off=(uint64_t)pc-im->base;
    if (off+4>im->size) die("pc beyond image",im->id);
    return le32(im->bytes+off);
}

static void add_read(Decoded *d,int r,unsigned role)
{
    if (r) { d->reads|=1u<<r; d->roles[r]|=role; }
}
static void add_write(Decoded *d,int r) { if (r) d->writes|=1u<<r; }

static Decoded decode(uint32_t w)
{
    Decoded d; uint32_t op=w>>26,rs=(w>>21)&31u,rt=(w>>16)&31u,rd=(w>>11)&31u,fn=w&63u;
    memset(&d,0,sizeof d); d.known=1; d.base=d.value=-1; d.imm=(int16_t)(w&0xffffu);
    if (op==0) {
        switch(fn) {
        case 0: case 2: case 3: add_read(&d,(int)rt,ROLE_ARITHMETIC); add_write(&d,(int)rd); break;
        case 4: case 6: case 7: add_read(&d,(int)rs,ROLE_ARITHMETIC); add_read(&d,(int)rt,ROLE_ARITHMETIC); add_write(&d,(int)rd); break;
        case 8: add_read(&d,(int)rs,ROLE_INDIRECT_TARGET); break;
        case 9: add_read(&d,(int)rs,ROLE_INDIRECT_TARGET); add_write(&d,(int)rd); break;
        case 12: case 13: break;
        case 16: case 18: add_write(&d,(int)rd); break;
        case 17: case 19: add_read(&d,(int)rs,ROLE_ARITHMETIC); break;
        case 24: case 25: case 26: case 27: add_read(&d,(int)rs,ROLE_ARITHMETIC); add_read(&d,(int)rt,ROLE_ARITHMETIC); break;
        case 32: case 33: case 34: case 35: case 36: case 37: case 38: case 39:
        case 42: case 43: add_read(&d,(int)rs,ROLE_ARITHMETIC); add_read(&d,(int)rt,ROLE_ARITHMETIC); add_write(&d,(int)rd); break;
        default: d.known=0; break;
        }
    } else if (op==1) {
        add_read(&d,(int)rs,ROLE_BRANCH); if (rt>=16&&rt<=19) add_write(&d,31);
        if (!(rt<=3||(rt>=16&&rt<=19))) d.known=0;
    } else if (op==2) {
        /* j */
    } else if (op==3) {
        add_write(&d,31);
    } else if ((op>=4&&op<=7)||(op>=0x14&&op<=0x17)) {
        add_read(&d,(int)rs,ROLE_BRANCH); if (op==4||op==5||op==0x14||op==0x15) add_read(&d,(int)rt,ROLE_BRANCH);
    } else if (op>=8&&op<=14) {
        add_read(&d,(int)rs,ROLE_ARITHMETIC); add_write(&d,(int)rt);
    } else if (op==15) {
        add_write(&d,(int)rt);
    } else if (op>=0x10&&op<=0x13) {
        if (rs==0||rs==2) add_write(&d,(int)rt);
        else if (rs==4||rs==6) add_read(&d,(int)rt,ROLE_ARITHMETIC);
        else if (rs==8) { if (rt>3) d.known=0; }
        /* all other encodings are coprocessor-local commands */
    } else if (op>=0x20&&op<=0x26) {
        d.is_load=1; d.width=(op==0x20||op==0x24)?1:(op==0x21||op==0x25)?2:4; d.base=(int)rs; d.value=(int)rt;
        add_read(&d,(int)rs,ROLE_MEMORY_BASE); if (op==0x22||op==0x26) add_read(&d,(int)rt,ROLE_MERGE_VALUE); add_write(&d,(int)rt);
    } else if (op==0x28||op==0x29||op==0x2a||op==0x2b||op==0x2e) {
        d.is_store=1; d.width=op==0x28?1:op==0x29?2:4; d.base=(int)rs; d.value=(int)rt;
        add_read(&d,(int)rs,ROLE_MEMORY_BASE); add_read(&d,(int)rt,ROLE_STORE_VALUE);
    } else if (op==0x30||op==0x31||op==0x32||op==0x33) {
        d.is_load=1; d.width=4; d.base=(int)rs; add_read(&d,(int)rs,ROLE_MEMORY_BASE);
    } else if (op==0x38||op==0x39||op==0x3a||op==0x3b) {
        d.is_store=1; d.width=4; d.base=(int)rs; d.value=-1; add_read(&d,(int)rs,ROLE_MEMORY_BASE);
    } else d.known=0;
    return d;
}

static int is_transfer(uint32_t w)
{
    uint32_t op=w>>26,fn=w&63u,rs=(w>>21)&31u,rt=(w>>16)&31u;
    return op==2||op==3||op==1||(op>=4&&op<=7)||(op>=0x14&&op<=0x17)||
           (op>=0x10&&op<=0x13&&rs==8&&rt<=3)||(op==0&&(fn==8||fn==9));
}
static int is_branch(uint32_t w)
{
    uint32_t op=w>>26,rs=(w>>21)&31u,rt=(w>>16)&31u;
    return op==1||(op>=4&&op<=7)||(op>=0x14&&op<=0x17)||(op>=0x10&&op<=0x13&&rs==8&&rt<=3);
}
static int is_likely(uint32_t w)
{
    uint32_t op=w>>26,rs=(w>>21)&31u,rt=(w>>16)&31u;
    return (op>=0x14&&op<=0x17)||(op==1&&(rt==2||rt==3||rt==18||rt==19))||
           (op>=0x10&&op<=0x13&&rs==8&&(rt==2||rt==3));
}
static int is_call(uint32_t w)
{
    uint32_t op=w>>26,rt=(w>>16)&31u;
    return op==3||(op==0&&(w&63u)==9)||(op==1&&rt>=16&&rt<=19);
}
static uint32_t direct_target(uint32_t w,uint32_t pc)
{
    uint32_t op=w>>26;
    if (op==2||op==3) return ((pc+4)&0xf0000000u)|((w&0x03ffffffu)<<2);
    return pc+4+((uint32_t)(int32_t)(int16_t)(w&0xffffu)<<2);
}

static int index_for(const Func *f,uint32_t pc)
{
    if (pc<f->entry||pc>=f->end||((pc-f->entry)&3u)) return -1;
    return (int)((pc-f->entry)/4);
}

/* Successors preserve the architectural delay slot.  If a delay word also has
 * a direct entry, the row is marked context-ambiguous and is not complete. */
static int successors(const Func *f,const uint32_t *code,int n,int i,int out[3])
{
    int m=0;
    if (i>0&&is_transfer(code[i-1])) {
        uint32_t p=code[i-1],op=p>>26,pc=f->entry+(uint32_t)(i-1)*4;
        if (is_branch(p)) {
            int t=index_for(f,direct_target(p,pc)); if (t>=0) out[m++]=t;
            if (!is_likely(p)&&i+1<n) out[m++]=i+1;
        } else if (is_call(p)) { if (i+1<n) out[m++]=i+1; }
        else if (op==2) { int t=index_for(f,direct_target(p,pc)); if (t>=0) out[m++]=t; }
        return m;
    }
    if (is_transfer(code[i])) {
        if (is_likely(code[i])&&i+2<n) out[m++]=i+2;
        if (i+1<n) out[m++]=i+1;
        return m;
    }
    if (i+1<n) out[m++]=i+1;
    return m;
}

static SpState sp_join(SpState a,SpState b)
{
    if (a.kind==SP_BOTTOM) return b;
    if (b.kind==SP_BOTTOM) return a;
    if (a.kind==SP_UNKNOWN||b.kind==SP_UNKNOWN) return (SpState){SP_UNKNOWN,0};
    if (a.delta!=b.delta) return (SpState){SP_UNKNOWN,0};
    return a;
}
static SpState sp_transfer(SpState s,uint32_t w,Decoded d)
{
    uint32_t op=w>>26,rs=(w>>21)&31u,rt=(w>>16)&31u;
    if (s.kind!=SP_EXACT) return s;
    if ((op==8||op==9)&&rs==29&&rt==29) { s.delta+=(int16_t)(w&0xffffu); return s; }
    if (d.writes&(1u<<29)) return (SpState){SP_UNKNOWN,0};
    return s;
}
static int same_sp(SpState a,SpState b) { return a.kind==b.kind&&(a.kind!=SP_EXACT||a.delta==b.delta); }

static void json_string(const char *s)
{
    putchar('"'); for (;*s;s++) { unsigned char c=(unsigned char)*s;
        if (c=='"'||c=='\\') printf("\\%c",c); else if (c<0x20) printf("\\u%04x",c); else putchar(c); }
    putchar('"');
}
static void pc_json(uint32_t pc) { printf("\"0x%08x\"",pc); }

static int role_pref(unsigned roles)
{
    if (roles&ROLE_MEMORY_BASE) return ROLE_MEMORY_BASE;
    if (roles&ROLE_STORE_VALUE) return ROLE_STORE_VALUE;
    if (roles&ROLE_INDIRECT_TARGET) return ROLE_INDIRECT_TARGET;
    if (roles&ROLE_BRANCH) return ROLE_BRANCH;
    if (roles&ROLE_MERGE_VALUE) return ROLE_MERGE_VALUE;
    return ROLE_ARITHMETIC;
}
static const char *role_name(int role)
{
    switch(role) { case ROLE_MEMORY_BASE:return "memory_base"; case ROLE_STORE_VALUE:return "store_value";
    case ROLE_INDIRECT_TARGET:return "indirect_target"; case ROLE_BRANCH:return "branch_predicate";
    case ROLE_MERGE_VALUE:return "unaligned_load_merge_value"; default:return "arithmetic"; }
}

static void analyse(const Func *f,int first)
{
    const Image *im=&IMAGES[f->image]; int n=(int)((f->end-f->entry)/4),i,j,changed;
    uint32_t *code=calloc((size_t)n,sizeof *code); Decoded *dec=calloc((size_t)n,sizeof *dec);
    uint8_t *reach=calloc((size_t)n,1),*arg_in=calloc((size_t)n,1),*v_in=calloc((size_t)n,1);
    uint8_t (*r_in)[10]=malloc((size_t)n*10),(*r_out)[10]=malloc((size_t)n*10);
    uint8_t (*m_in)[10]=malloc((size_t)n*10),(*m_out)[10]=malloc((size_t)n*10);
    SpState *sp_in=calloc((size_t)n,sizeof *sp_in),*sp_out=calloc((size_t)n,sizeof *sp_out);
    int arg_pc[4]={-1,-1,-1,-1},arg_pointer_pc[4]={-1,-1,-1,-1}; unsigned arg_role[4]={0};
    int save_slot[10],save_pc[10],save_have[10]={0},save_ambig[10]={0}; uint32_t unknown_count=0,amb_count=0;
    int any_call=0,min_sp=0,max_sp=0,sp_nonconstant=0;
    int extent_positive_sp_adjust=0,extent_negative_sp_adjust=0;
    int stack_offsets[MAX_STACK_SLOTS],stack_count=0,stack_pc[MAX_STACK_SLOTS];
    uint64_t (*stack_in)[2]=calloc((size_t)n,sizeof *stack_in),(*stack_out)[2]=calloc((size_t)n,sizeof *stack_out);
    if (!code||!dec||!reach||!arg_in||!v_in||!r_in||!r_out||!m_in||!m_out||!sp_in||!sp_out||!stack_in||!stack_out)
        die("out of memory",f->name);
    if (n<=0||n>MAX_WORDS) die("function exceeds probe word limit",f->name);
    memset(r_in,R_BOTTOM,(size_t)n*10); memset(r_out,R_BOTTOM,(size_t)n*10);
    memset(m_in,R_BOTTOM,(size_t)n*10); memset(m_out,R_BOTTOM,(size_t)n*10);
    for (i=0;i<10;i++) save_slot[i]=save_pc[i]=-1;
    for (i=0;i<MAX_STACK_SLOTS;i++) stack_pc[i]=-1;
    for (i=0;i<n;i++) {
        int32_t simm;
        code[i]=word_at(im,f->entry+(uint32_t)i*4); dec[i]=decode(code[i]);
        simm=(int16_t)(code[i]&0xffffu);
        if (((code[i]>>26)==8||(code[i]>>26)==9)&&
            ((code[i]>>21)&31u)==29&&((code[i]>>16)&31u)==29) {
            if (simm>extent_positive_sp_adjust) extent_positive_sp_adjust=(int)simm;
            if (simm<0) extent_negative_sp_adjust=1;
        }
    }

    /* Context-sensitive delay-slot entry audit, exact direct-target set. */
    for (i=0;i<n;i++) if (is_branch(code[i])||(code[i]>>26)==2||(code[i]>>26)==3) {
        int t=index_for(f,direct_target(code[i],f->entry+(uint32_t)i*4));
        if (t>0&&is_transfer(code[t-1])) amb_count++;
    }

    /* Reachability. */
    reach[0]=1; do { changed=0; for (i=0;i<n;i++) if (reach[i]) { int s[3],ns=successors(f,code,n,i,s);
        for (j=0;j<ns;j++) if (!reach[s[j]]) { reach[s[j]]=1; changed=1; } } } while(changed);
    for (i=0;i<n;i++) if (reach[i]&&!dec[i].known) unknown_count++;

    /* Stack delta dataflow. */
    sp_in[0]=(SpState){SP_EXACT,0}; do { changed=0; for (i=0;i<n;i++) if (reach[i]&&sp_in[i].kind!=SP_BOTTOM) {
        SpState o=sp_transfer(sp_in[i],code[i],dec[i]); sp_out[i]=o;
        if (o.kind==SP_EXACT&&o.delta<min_sp) min_sp=o.delta;
        if (o.kind==SP_EXACT&&o.delta>max_sp) max_sp=o.delta;
        if (o.kind==SP_UNKNOWN) sp_nonconstant=1;
        int s[3],ns=successors(f,code,n,i,s); for (j=0;j<ns;j++) { SpState q=sp_join(sp_in[s[j]],o);
            if (!same_sp(q,sp_in[s[j]])) { sp_in[s[j]]=q; changed=1; } }
    } } while(changed);

    /* Incoming argument liveness: union means some entry path still carries it. */
    arg_in[0]=15; do { changed=0; for (i=0;i<n;i++) if (reach[i]) {
        uint8_t o=(uint8_t)(arg_in[i]&~((dec[i].writes>>4)&15u));
        int s[3],ns=successors(f,code,n,i,s),prev_call=i>0&&is_call(code[i-1]);
        if (prev_call) o=0;
        for (j=0;j<ns;j++) { uint8_t q=arg_in[s[j]]|o; if (q!=arg_in[s[j]]) {arg_in[s[j]]=q;changed=1;} }
    } } while(changed);
    for (i=0;i<n;i++) if (reach[i]) for (j=0;j<4;j++) if ((arg_in[i]&(1u<<j))&&(dec[i].reads&(1u<<(j+4)))) {
        if (arg_pc[j]<0) { arg_pc[j]=i; arg_role[j]=(unsigned)role_pref(dec[i].roles[j+4]); }
        if ((dec[i].roles[j+4]&ROLE_MEMORY_BASE)&&arg_pointer_pc[j]<0) arg_pointer_pc[j]=i;
    }

    /* First pass: prove which stores still carry the incoming callee-register
     * value without assuming that any load is a restore.  This prevents an
     * outgoing-argument store of a locally modified s-register from becoming
     * a false canonical save slot. */
    for (j=0;j<10;j++) r_in[0][j]=R_ENTRY;
    do { changed=0; for (i=0;i<n;i++) if (reach[i]&&r_in[i][0]!=R_BOTTOM) {
        memcpy(r_out[i],r_in[i],10);
        for (j=0;j<10;j++) if (dec[i].writes&(1u<<CALLEE_REGS[j]))
            r_out[i][j]=R_MODIFIED;
        { int s[3],ns=successors(f,code,n,i,s); for (int z=0;z<ns;z++) for (j=0;j<10;j++) {
            uint8_t old=r_in[s[z]][j],q;
            if (old==R_BOTTOM) q=r_out[i][j]; else q=old==r_out[i][j]?old:R_UNKNOWN;
            if (q!=old) { r_in[s[z]][j]=q; changed=1; }
        } }
    } } while(changed);

    /* A canonical save candidate must store the proved incoming value and
     * have a later matching reload before any intervening overwrite of that
     * entry-SP slot.  Extra outgoing/local stores are therefore not treated
     * as competing saves. */
    for (j=0;j<10;j++) for (i=0;i<n;i++)
        if (reach[i]&&r_in[i][j]==R_ENTRY&&sp_in[i].kind==SP_EXACT&&
            dec[i].is_store&&dec[i].width==4&&dec[i].base==29&&dec[i].value==CALLEE_REGS[j]) {
            int slot=sp_in[i].delta+dec[i].imm,k,paired=0;
            for (k=0;k<n;k++) if (reach[k]&&sp_in[k].kind==SP_EXACT) {
                int kslot=sp_in[k].delta+dec[k].imm;
                if (dec[k].is_load&&dec[k].width==4&&dec[k].base==29&&
                    dec[k].value==CALLEE_REGS[j]&&kslot==slot) { paired=1; break; }
            }
            if (paired) {
                if (!save_have[j]) { save_slot[j]=slot; save_pc[j]=i; save_have[j]=1; }
                else if (save_slot[j]!=slot) save_ambig[j]=1;
            }
        }

    /* Second pass: only an unambiguous paired slot may restore the incoming
     * value.  Entry $ra remains merely an external entry value; this pass does
     * not assert that call-link semantics produced it. */
    memset(r_in,R_BOTTOM,(size_t)n*10); memset(r_out,R_BOTTOM,(size_t)n*10);
    memset(m_in,R_BOTTOM,(size_t)n*10); memset(m_out,R_BOTTOM,(size_t)n*10);
    for (j=0;j<10;j++) { r_in[0][j]=R_ENTRY; m_in[0][j]=R_MODIFIED; }
    do { changed=0; for (i=0;i<n;i++) if (reach[i]&&r_in[i][0]!=R_BOTTOM) {
        memcpy(r_out[i],r_in[i],10);
        memcpy(m_out[i],m_in[i],10);
        for (j=0;j<10;j++) if (dec[i].writes&(1u<<CALLEE_REGS[j])) {
            int restored=dec[i].is_load&&dec[i].width==4&&dec[i].base==29&&dec[i].value==CALLEE_REGS[j]&&
                sp_in[i].kind==SP_EXACT&&!save_ambig[j]&&save_have[j]&&
                sp_in[i].delta+dec[i].imm==save_slot[j];
            r_out[i][j]=(uint8_t)(restored?m_in[i][j]:R_MODIFIED);
        }
        for (j=0;j<10;j++) if (sp_in[i].kind==SP_EXACT&&!save_ambig[j]&&save_have[j]&&
            dec[i].is_store&&dec[i].base==29&&sp_in[i].delta+dec[i].imm==save_slot[j]) {
            m_out[i][j]=(uint8_t)(dec[i].width==4&&dec[i].value==CALLEE_REGS[j]?r_in[i][j]:R_MODIFIED);
        }
        int s[3],ns=successors(f,code,n,i,s); for (int z=0;z<ns;z++) for (j=0;j<10;j++) {
            uint8_t old=r_in[s[z]][j],q,oldm=m_in[s[z]][j],qm;
            if (old==R_BOTTOM) q=r_out[i][j]; else q=old==r_out[i][j]?old:R_UNKNOWN;
            if (oldm==R_BOTTOM) qm=m_out[i][j]; else qm=oldm==m_out[i][j]?oldm:R_UNKNOWN;
            if (q!=old) { r_in[s[z]][j]=q; changed=1; }
            if (qm!=oldm) { m_in[s[z]][j]=qm; changed=1; }
        }
    } } while(changed);

    /* Definite direct v0/v1 writes. A call is not assumed to write either: the
     * callee ABI may permit a clobber, but that is not an instruction proof. */
    { uint8_t *seen=calloc((size_t)n,1); memset(v_in,0,(size_t)n); seen[0]=1;
      do { changed=0; for (i=0;i<n;i++) if (reach[i]&&seen[i]) { uint8_t o=v_in[i];
        if (dec[i].writes&(1u<<2)) o|=1;
        if (dec[i].writes&(1u<<3)) o|=2;
        int s[3],ns=successors(f,code,n,i,s);for(j=0;j<ns;j++){uint8_t q=seen[s[j]]?(uint8_t)(v_in[s[j]]&o):o;
          if(!seen[s[j]]||q!=v_in[s[j]]){seen[s[j]]=1;v_in[s[j]]=q;changed=1;}}
      }}while(changed); free(seen); }

    /* Candidate incoming stack slots, then may-unwritten dataflow. */
    for (i=0;i<n;i++) if (reach[i]&&sp_in[i].kind==SP_EXACT&&dec[i].is_load&&dec[i].base==29) {
        int off=sp_in[i].delta+dec[i].imm,k; if (off<16) continue;
        for(k=0;k<stack_count&&stack_offsets[k]!=off;k++) { }
        if(k==stack_count){if(stack_count==MAX_STACK_SLOTS)die("too many stack slots",f->name);stack_offsets[stack_count++]=off;}
    }
    if (stack_count) {
        stack_in[0][0]=stack_count>=64?UINT64_MAX:((1ull<<stack_count)-1ull);
        stack_in[0][1]=stack_count<=64?0:(stack_count==128?UINT64_MAX:((1ull<<(stack_count-64))-1ull));
        do { changed=0; for(i=0;i<n;i++) if(reach[i]) { uint64_t o0=stack_in[i][0],o1=stack_in[i][1];
            if(sp_in[i].kind==SP_EXACT&&dec[i].is_store&&dec[i].base==29){int off=sp_in[i].delta+dec[i].imm;
                for(j=0;j<stack_count;j++)if(stack_offsets[j]==off){if(j<64)o0&=~(1ull<<j);else o1&=~(1ull<<(j-64));}}
            int s[3],ns=successors(f,code,n,i,s);for(j=0;j<ns;j++){uint64_t q0=stack_in[s[j]][0]|o0,q1=stack_in[s[j]][1]|o1;
                if(q0!=stack_in[s[j]][0]||q1!=stack_in[s[j]][1]){stack_in[s[j]][0]=q0;stack_in[s[j]][1]=q1;changed=1;}}
        }}while(changed);
        for(i=0;i<n;i++)if(reach[i]&&sp_in[i].kind==SP_EXACT&&dec[i].is_load&&dec[i].base==29){int off=sp_in[i].delta+dec[i].imm;
            for(j=0;j<stack_count;j++)if(stack_offsets[j]==off&&((j<64?(stack_in[i][0]>>j):(stack_in[i][1]>>(j-64)))&1u)&&stack_pc[j]<0)stack_pc[j]=i;}
    }

    for (i=0;i<n;i++) if (reach[i]) { if (is_call(code[i])) any_call=1;
        if ((dec[i].writes&(1u<<29))&&!(((code[i]>>26)==8||(code[i]>>26)==9)&&((code[i]>>21)&31u)==29&&((code[i]>>16)&31u)==29)) sp_nonconstant=1; }

    printf("%s{\"image\":",first?"":","); json_string(im->id); printf(",\"entry\":");pc_json(f->entry);printf(",\"end_exclusive\":");pc_json(f->end);printf(",\"name\":");json_string(f->name);
    {int rc=0;for(i=0;i<n;i++)if(reach[i])rc++;
     printf(",\"instruction_words\":%d,\"reachable_words\":%d,\"decoder_unknown_pcs\":[",n,rc);}
    {int sep=0; for(i=0;i<n;i++)if(reach[i]&&!dec[i].known){if(sep++)putchar(',');pc_json(f->entry+(uint32_t)i*4);} }
    printf("],\"cfg_context_sensitive_delay_entries\":[");
    {int sep=0;for(i=0;i<n;i++)if(is_branch(code[i])||(code[i]>>26)==2||(code[i]>>26)==3){int t=index_for(f,direct_target(code[i],f->entry+(uint32_t)i*4));if(t>0&&is_transfer(code[t-1])){if(sep++)putchar(',');pc_json(f->entry+(uint32_t)t*4);}}}
    printf("],\"argument_registers\":[");
    {int sep=0;for(j=0;j<4;j++)if(arg_pc[j]>=0){uint32_t pc=f->entry+(uint32_t)arg_pc[j]*4;if(sep++)putchar(',');
        printf("{\"register\":\"a%d\",\"proof_pc\":",j);pc_json(pc);printf(",\"proof_word\":\"0x%08x\",\"proof_role\":",code[arg_pc[j]]);json_string(role_name((int)arg_role[j]));
        printf(",\"pointer_use_pc\":");if(arg_pointer_pc[j]>=0)pc_json(f->entry+(uint32_t)arg_pointer_pc[j]*4);else printf("null");putchar('}');}}
    {int inherited_entry=max_sp>0||(extent_positive_sp_adjust>0&&!extent_negative_sp_adjust);
     int stack_basis_known=f->entry_sp_call_proved&&!sp_nonconstant&&!inherited_entry;
     printf("],\"stack_argument_analysis\":{\"classification\":");json_string(stack_basis_known?"call_entry_sp_anchored":inherited_entry?"inherited_or_unbalanced_entry_sp":sp_nonconstant?"variable_or_unknown_sp":"unknown_entry_sp_provenance");printf(",\"entry_call_link_proved\":%s,\"entry_call_witness_pc\":",f->entry_sp_call_proved?"true":"false");if(f->entry_sp_call_proved)pc_json(f->entry_call_witness_pc);else printf("null");printf(",\"entry_call_witness_word\":");if(f->entry_sp_call_proved)printf("\"0x%08x\"",word_at(im,f->entry_call_witness_pc));else printf("null");printf(",\"maximum_positive_sp_delta\":%d,\"largest_positive_sp_adjustment_bytes\":%d,\"positive_sp_adjustment_without_extent_push\":%s},\"stack_arguments\":[",max_sp,extent_positive_sp_adjust,extent_positive_sp_adjust>0&&!extent_negative_sp_adjust?"true":"false");
     {int sep=0;for(j=0;j<stack_count;j++)if(stack_basis_known&&stack_pc[j]>=0){if(sep++)putchar(',');printf("{\"entry_sp_offset\":%d,\"proof_pc\":",stack_offsets[j]);pc_json(f->entry+(uint32_t)stack_pc[j]*4);printf(",\"proof_word\":\"0x%08x\"}",code[stack_pc[j]]);}}
     printf("],\"unclassified_entry_relative_stack_loads\":[");
     {int sep=0;for(j=0;j<stack_count;j++)if(!stack_basis_known&&stack_pc[j]>=0){if(sep++)putchar(',');printf("{\"entry_relative_offset\":%d,\"proof_pc\":",stack_offsets[j]);pc_json(f->entry+(uint32_t)stack_pc[j]*4);printf(",\"proof_word\":\"0x%08x\"}",code[stack_pc[j]]);}}
    }
    printf("],\"entry_ra_call_link_proved\":false,\"entry_ra_provenance\":\"unknown_external_entry_value\",\"normal_return_sites\":[],\"incoming_ra_continuation_sites\":[");
    {int sep=0;for(i=0;i<n;i++)if(reach[i]&&code[i]==0x03e00008u&&r_in[i][9]==R_ENTRY){if(sep++)putchar(',');pc_json(f->entry+(uint32_t)i*4);}}
    printf("],\"non_entry_ra_jr_ra_sites\":[");
    {int sep=0;for(i=0;i<n;i++)if(reach[i]&&code[i]==0x03e00008u&&r_in[i][9]!=R_ENTRY){if(sep++)putchar(',');printf("{\"pc\":");pc_json(f->entry+(uint32_t)i*4);printf(",\"ra_state\":\"%s\"}",r_in[i][9]==R_MODIFIED?"locally_modified":r_in[i][9]==R_UNKNOWN?"unknown_at_join":"unreached");}}
    printf("]");
    {int continuations=0,allv0=1,allv1=1,anyv0=0,anyv1=0,frame_bal=1;
     for(i=0;i<n;i++)if(reach[i]){if(dec[i].writes&(1u<<2))anyv0=1;if(dec[i].writes&(1u<<3))anyv1=1;
        if(code[i]==0x03e00008u&&r_in[i][9]==R_ENTRY){int d=i+1;continuations++;if(d>=n){allv0=allv1=frame_bal=0;}else{uint8_t ov=v_in[d];if(dec[d].writes&(1u<<2))ov|=1;if(dec[d].writes&(1u<<3))ov|=2;if(!(ov&1))allv0=0;if(!(ov&2))allv1=0;SpState so=sp_transfer(sp_in[d],code[d],dec[d]);if(so.kind!=SP_EXACT||so.delta!=0)frame_bal=0;}}}
     printf(",\"return_convention\":{\"classification\":");
     if(continuations)json_string("unknown_entry_ra_provenance");
     else json_string("unknown_no_proved_normal_return");
     printf(",\"normal_return_count\":0,\"incoming_ra_continuation_count\":%d,\"v0_written_on_every_return_path\":null,\"v1_written_on_every_return_path\":null,\"v0_written_on_every_incoming_ra_continuation_path\":%s,\"v1_written_on_every_incoming_ra_continuation_path\":%s,\"v0_written_on_any_path\":%s,\"v1_written_on_any_path\":%s}",continuations,continuations&&allv0?"true":"false",continuations&&allv1?"true":"false",anyv0?"true":"false",anyv1?"true":"false");
     {int inherited_entry=max_sp>0||(extent_positive_sp_adjust>0&&!extent_negative_sp_adjust);
      printf(",\"frame\":{\"kind\":");json_string(inherited_entry?"inherited_or_unbalanced":sp_nonconstant?"variable_or_unknown":min_sp?"fixed":"none");printf(",\"size_bytes\":");if(sp_nonconstant||inherited_entry)printf("null");else printf("%d",-min_sp);printf(",\"entry_sp_basis_known\":%s,\"minimum_sp_delta\":%d,\"maximum_sp_delta\":%d,\"sp_state_has_unknown\":%s,\"positive_sp_adjustment_without_extent_push\":%s,\"balanced_on_all_normal_returns\":null,\"balanced_on_all_incoming_ra_continuations\":%s}",f->entry_sp_call_proved&&!sp_nonconstant&&!inherited_entry?"true":"false",min_sp,max_sp,sp_nonconstant?"true":"false",extent_positive_sp_adjust>0&&!extent_negative_sp_adjust?"true":"false",continuations&&frame_bal?"true":"false");}
    }
    printf(",\"callee_saved\":[");
    for(j=0;j<10;j++){int continuations=0,preserved=1,restore_count=0;if(j)putchar(',');
        for(i=0;i<n;i++)if(reach[i]&&code[i]==0x03e00008u&&r_in[i][9]==R_ENTRY){int d=i+1;continuations++;if(d>=n)preserved=0;else{uint8_t st=r_out[d][j];if(st!=R_ENTRY)preserved=0;}}
        for(i=0;i<n;i++)if(reach[i]&&dec[i].is_load&&dec[i].width==4&&dec[i].base==29&&dec[i].value==CALLEE_REGS[j]&&sp_in[i].kind==SP_EXACT&&save_have[j]&&sp_in[i].delta+dec[i].imm==save_slot[j]&&m_in[i][j]==R_ENTRY)restore_count++;
        printf("{\"register\":");json_string(REGS[CALLEE_REGS[j]]);printf(",\"status\":");
        if(!continuations)json_string("not_classified_without_incoming_ra_continuation");else if(save_ambig[j])json_string("unknown_ambiguous_save_slot");else if(preserved&&save_have[j])json_string("balanced_save_restore_on_incoming_ra_continuations");else if(preserved)json_string("preserved_without_save_on_incoming_ra_continuations");else json_string("not_preserved_on_every_incoming_ra_continuation");
        printf(",\"entry_sp_slot\":");if(save_have[j]&&!save_ambig[j])printf("%d",save_slot[j]);else printf("null");printf(",\"save_pc\":");if(save_pc[j]>=0)pc_json(f->entry+(uint32_t)save_pc[j]*4);else printf("null");printf(",\"matching_restore_instructions\":%d,\"ambiguous_save_slots\":%s}",restore_count,save_ambig[j]?"true":"false");
    }
    printf("],\"caller_saved_written\":[");
    {int sep=0;for(j=0;j<17;j++){int reg=CALLER_REGS[j],first_write=-1;for(i=0;i<n;i++)if(reach[i]&&(dec[i].writes&(1u<<reg))){first_write=i;break;}if(first_write>=0||any_call){if(sep++)putchar(',');printf("{\"register\":");json_string(REGS[reg]);printf(",\"direct_instruction_write\":%s,\"first_direct_write_pc\":",first_write>=0?"true":"false");if(first_write>=0)pc_json(f->entry+(uint32_t)first_write*4);else printf("null");printf(",\"first_direct_write_word\":");if(first_write>=0)printf("\"0x%08x\"",code[first_write]);else printf("null");printf(",\"may_be_clobbered_by_nested_call\":%s}",any_call?"true":"false");}}}
    printf("],\"direct_gp_writes\":[");
    {int sep=0;for(i=0;i<n;i++)if(reach[i]&&dec[i].is_store&&dec[i].base==28){if(sep++)putchar(',');printf("{\"pc\":");pc_json(f->entry+(uint32_t)i*4);printf(",\"offset\":%d,\"address\":",dec[i].imm);pc_json(im->gp+(uint32_t)dec[i].imm);printf(",\"width\":%d}",dec[i].width);}}
    printf("],\"decoded_stores\":[");
    {int sep=0;for(i=0;i<n;i++)if(reach[i]&&dec[i].is_store){if(sep++)putchar(',');
        printf("{\"pc\":");pc_json(f->entry+(uint32_t)i*4);printf(",\"base_register\":");
        if(dec[i].base>=0)json_string(REGS[dec[i].base]);else printf("null");
        printf(",\"offset\":%d,\"width\":%d}",dec[i].imm,dec[i].width);}}
    {int stores=0,stackstores=0;for(i=0;i<n;i++)if(reach[i]&&dec[i].is_store){stores++;if(dec[i].base==29)stackstores++;}
     printf("],\"decoded_store_sites\":%d,\"stack_store_sites\":%d,\"has_nested_call\":%s,\"mechanically_complete\":%s}",stores,stackstores,any_call?"true":"false",(!unknown_count&&!amb_count)?"true":"false");}
    free(code);free(dec);free(reach);free(arg_in);free(v_in);free(r_in);free(r_out);free(m_in);free(m_out);free(sp_in);free(sp_out);free(stack_in);free(stack_out);
}

static void emit_ra_hazards(void)
{
    int h; printf("],\"ra_general_jump_caution_pairs\":[");
    for(h=0;h<NRA_HAZARDS;h++) {
        RaHazard *x=&RA_HAZARDS[h]; Image *im=&IMAGES[x->image];
        uint32_t site=word_at(im,x->site_pc);
        uint32_t predecessor=word_at(im,x->observed_target-8);
        if(h)putchar(',');
        printf("{\"image\":");json_string(im->id);printf(",\"site_pc\":");pc_json(x->site_pc);
        printf(",\"site_word\":\"0x%08x\",\"site_is_jr_ra\":%s,\"observed_target\":",site,site==0x03e00008u?"true":"false");pc_json(x->observed_target);
        printf(",\"target_minus_8_pc\":");pc_json(x->observed_target-8);
        printf(",\"target_minus_8_word\":\"0x%08x\",\"target_minus_8_is_call\":%s}",predecessor,is_call(predecessor)?"true":"false");
    }
    printf("]");
}

static void emit_hoists(void)
{
    int h; printf(",\"hoisted_load_checks\":[");
    for(h=0;h<NHOISTS;h++){Hoist *x=&HOISTS[h];Image *im=&IMAGES[x->image];uint32_t w=word_at(im,x->load_pc);Decoded d=decode(w);int pattern=0;
        if(x->load_pc>=im->base+8){uint32_t cmp=word_at(im,x->load_pc-8),add=word_at(im,x->load_pc-4),br=word_at(im,x->load_pc+4);
            int cond=(int)((cmp>>11)&31u),cmp_rs=(int)((cmp>>21)&31u),cmp_rt=(int)((cmp>>16)&31u);
            int idx=(int)((add>>11)&31u),add_rs=(int)((add>>21)&31u),add_rt=(int)((add>>16)&31u);
            uint32_t cop=cmp>>26,aop=add>>26,bop=br>>26;
            int cmp_ok=cop==0&&((cmp&63u)==42||(cmp&63u)==43)&&cond!=0;
            int add_ok=aop==0&&((add&63u)==32||(add&63u)==33)&&idx!=0&&
                (idx==cmp_rs||idx==cmp_rt)&&
                ((add_rs==idx&&add_rt!=idx)||(add_rt==idx&&add_rs!=idx));
            int load_ok=d.known&&d.is_load&&d.base==idx&&d.imm==0;
            int branch_ok=(bop==4||bop==5)&&
                ((((br>>21)&31u)==(uint32_t)cond&&((br>>16)&31u)==0)||
                 (((br>>16)&31u)==(uint32_t)cond&&((br>>21)&31u)==0));
            pattern=cmp_ok&&add_ok&&load_ok&&branch_ok;
        }
        if(h)putchar(',');
        printf("{\"image\":");json_string(im->id);printf(",\"load_pc\":");pc_json(x->load_pc);printf(",\"logged_pc\":");pc_json(x->logged_pc);printf(",\"word\":\"0x%08x\",\"decoded_as_load\":%s,\"contiguous_idiom_recognized\":%s}",w,d.is_load?"true":"false",pattern?"true":"false");
    }
    printf("]}");
}

int main(int argc,char **argv)
{
    int i;if(argc!=2){fprintf(stderr,"usage: %s MANIFEST\n",argv[0]);return 2;}
    read_manifest(argv[1]);printf("{\"schema\":\"abl-phase4-f01-abi-probe/2\",\"decoder_owner\":\"compiled_c\",\"rows\":[");
    for(i=0;i<NFUNCS;i++) analyse(&FUNCS[i],i==0);
    emit_ra_hazards();emit_hoists();putchar('\n');
    for(i=0;i<NIMAGES;i++) free(IMAGES[i].bytes);
    return 0;
}
